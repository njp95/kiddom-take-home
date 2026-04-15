import logging
import json
import tempfile
from typing import Optional
from kubernetes import client, config, utils
from kubernetes.client.rest import ApiException

log = logging.getLogger(__name__)

# Load config: in-cluster when running in a pod, kubeconfig for local dev
try:
    config.load_incluster_config()
except config.ConfigException:
    config.load_kube_config()

v1 = client.CoreV1Api()
custom_objects = client.CustomObjectsApi()

def create_namespace(name: str, labels: dict = None, annotations: dict = None):
    meta = client.V1ObjectMeta(name=name, labels=labels, annotations=annotations)
    body = client.V1Namespace(metadata=meta)
    try:
        v1.create_namespace(body=body)
        log.info(f"Created namespace {name}")
    except ApiException as e:
        if e.status == 409:
            log.info(f"Namespace {name} already exists — skipping create")
        else:
            raise

def delete_namespace(name: str):
    try:
        v1.delete_namespace(name=name)
        log.info(f"Deleted namespace {name}")
    except ApiException as e:
        if e.status != 404: # Ignore 'NotFound'
            raise

def list_pr_namespaces():
    # Only list namespaces with our specific label 
    ret = v1.list_namespace(label_selector="ephemeral-env=true")
    return [{"metadata": {"name": ns.metadata.name, "annotations": ns.metadata.annotations}} 
            for ns in ret.items]

def apply_manifest(yaml_content: str, namespace: str):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as f:
        f.write(yaml_content)
        f.flush()
        try:
            # Use the ApiClient to apply the manifest
            utils.create_from_yaml(client.ApiClient(), f.name, namespace=namespace)
        except utils.FailToCreateError as e:
            # Check if the failure is just because the resource already exists
            for failure in e.api_exceptions:
                if failure.status == 409:
                    log.debug("Resource already exists, skipping...")
                    continue
                raise e