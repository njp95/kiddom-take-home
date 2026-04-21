## Setup:
In project root:
1. `make setup` will create the cluster, build and deploy the controller and ingress
2. `make simulate-open PR=n` will simulate the opening of a PR, with `n` being an int.
3. You will see with `kubectl get ns` that the new namespace has been created, along with an API and DB pod
4. `curl  http://pr-n.localenv.dev --resolve pr-n.localenv.dev:80:127.0.0.1`, with `n` being the PR number, will return the message set in the values
5. Change the message in the local `/manifests/values.yaml` file for the API pod, and run `make simulate-sync` to simulate a push to a PR
6. Run step 4 again to see the modified value
7. `make simulate-close` to tear down the environment