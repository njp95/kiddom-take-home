How does your namespace/isolation model work, and what are its limits? When would you choose cluster isolation instead?
- My repo contains a manifests folder that includes the templates for my api and database services, as well as a values file.
  I have also created a controller Docker image based around a Fast API that will respond to repo webhook events and behave accordingly.
  When a PR is opened, the controller will provision a new namespace with the changes to the manifests folder reflected in an api
  and db pod. When a change is made to the PR, the controller will replace the pod with the modified spec. When a PR is closed, the
  namespace and resources will be destroyed. 

  Some limitations of this model in its current form include DNS routing for the ephemeral environments and the Smee sidecar. 
  It is possible to curl them from a local machine but it requires adding a resolve flag, or updating the `/etc/hosts` file. 
  For production, we would want to use something like cert manager. Another limitation is the Smee sidecar. I opted to use smee 
  to create a tunnel for the webhook for simplicity, but in production I would want to set up an sturdier endpoint.

  I would want to choose cluster isolation instead for separating production from testing and development. In a real world environment,
  I would expect a standardized branch naming convention (something like feature/jira-ticket), and the controller to listen to PRs from 
  feature branches. When these have been tested, they can be promoted to testing, where the controller could listen to a different branch
  and/or cluster. Same would go for production changes. Cluster isolation would allow for greater control over who can access production,
  and ease resource usage on the cluster. 

How are secrets handled per environment? What are the risks of your approach?
- As it stands, I opted to use a `.env` file and hardcoded the secrets (currently just the GitHub PAT and webhook secret), without commiting 
  this file. For this POC, I did not feel a secrets manager would be entirely in scope. However, for production, I would opt to use a tool 
  like SOPS. This would allow all contributors to the repo to encrypt and commit their secrets for ease of use and access in a Kubernetes environment.

  A risk of this approach would be a compromised SOPS encryption key, which could partially be mitigated through proper access controls wherever the key
  is stored, and rotating it as needed. There is also the risk of a contributor commiting an unencrypted secret, which could be mitigated through
  proper training for the tool.

How do you handle stateful services — databases, queues? What's your strategy for seeding test data?
- Stateful services could be backed by a PVC. This would ensure that any changes to the manifest for the DB or queue would not impact data that needs
  to persist across commits. Of course, upon teardown of the namespace with the closure of a PR or end of a TTL, the PVC would be erased, however 
  given these environments are meant to be ephemeral, I think that is acceptable for the use case.

What does your cleanup strategy look like? What can go wrong with it?
- The cleanup strategy is implemented both by the closure of a PR and a TTL for the ephemeral environments. If there is a `pull_request.closed` webhook
  event, that will trigger the controller to shut down the environment. Alternatively, there is a background process on the controller that shuts down
  any environment with a `created_at` older than the TTL.

  Since closing a PR is often an intentional process, there is more that could go wrong with the TTL. There is the risk that a TTL is hit while 
  an engineer is still working with their environment. To mitigate this, we would want to set a long enough TTL, perhaps a week or more. We could also
  ensure that when a change is made to the PR, the controller updates the namespace's `created_at` to restart the clock.

What would need to change to make this production-grade? Be specific.
- I would want the manifests and controller to be managed in separate repositories. For the sake of this demo, it made sense to keep them contained to one.
  In a production environment, one repo would contain the manifests, likely packaged in a Helm chart and published to a shared registry, and the controller
  would be codified in its own repo as a separate project. I may even want to keep the values for the Helm chart in a separate repo as well.
  The controller would then listen to the values repo for PR events, and use the changes pushed from the webhook events as values for a new Helm chart,
  pulled from the registry.
