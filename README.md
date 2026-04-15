How does your namespace/isolation model work, and what are its limits? When would you choose cluster isolation instead?
How are secrets handled per environment? What are the risks of your approach?
How do you handle stateful services — databases, queues? What's your strategy for seeding test data? qq
What does your cleanup strategy look like? What can go wrong with it?

What would need to change to make this production-grade? Be specific.
- I would want the manifests and controller to be managed in separate repositories. For the sake of this demo, it made sense to keep them contained to one.
  In a production environment, one repo would contain the manifests, likely packaged in a Helm chart and published to a shared registry, and the controller
  would be codified in its own repo as a separate project. I may even want to keep the values for the Helm chart in a separate repo as well.
  The controller would then listen to the values repo for PR events, and use the changes pushed from the webhook events as values for a new Helm chart,
  pulled from the registry.