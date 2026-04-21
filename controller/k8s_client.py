import logging
import time
from kubernetes import client, config, dynamic
from kubernetes.client.rest import ApiException
import yaml as pyyaml



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

def wait_for_namespace_deletion(name: str, timeout: int = 60, interval: float = 2.0):
    """Block until the namespace is fully gone or timeout (seconds) is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            v1.read_namespace(name=name)
            log.debug("Namespace %s still terminating — waiting...", name)
            time.sleep(interval)
        except ApiException as e:
            if e.status == 404:
                log.info("Namespace %s is gone", name)
                return
            raise
    raise TimeoutError(f"Namespace {name} did not finish terminating within {timeout}s")

def get_local_values_override() -> str | None:
    """Return values.yaml content from the local-values-override ConfigMap, or None if absent."""
    try:
        cm = v1.read_namespaced_config_map(name="local-values-override", namespace="default")
        return cm.data.get("values.yaml")
    except ApiException as e:
        if e.status == 404:
            return None
        raise


def list_pr_namespaces():
    # Only list namespaces with our specific label 
    ret = v1.list_namespace(label_selector="ephemeral-env=true")
    return [{"metadata": {"name": ns.metadata.name, "annotations": ns.metadata.annotations}} 
            for ns in ret.items]

def apply_manifest(yaml_content: str, namespace: str):
    dyn = dynamic.DynamicClient(client.ApiClient())
    for doc in pyyaml.safe_load_all(yaml_content):
        if doc is None:
            continue
        resource = dyn.resources.get(api_version=doc["apiVersion"], kind=doc["kind"])
        name = doc["metadata"]["name"]
        resource.server_side_apply(
            body=doc,
            name=name,
            namespace=namespace,
            field_manager="lifecycle-controller",
            force_conflicts=True,
        )
        log.debug("Applied %s/%s", doc["kind"], name)