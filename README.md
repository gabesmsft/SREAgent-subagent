# SRE Agent Demo POC: Custom Subagent

A minimal proof-of-concept showing how to use a custom subagent to invoke tools and to be triggered via an incident response plan and scheduled task.

In this demo, we will use a custom subagent that invokes tools on a custom MCP server to do resource health checks.


## Step 1 — Deploy an MCP Server

Refer to [this page](https://github.com/azureossd/Container-Apps/tree/main/MCP_server) to deploy an MCP server on a Container App. You will need to deploy the Container App Environment and Container App, but you can deploy each with a button click without having to deploy code or containers. Make note of the mcp-api-key you enter when creating the Container App, and the URL of the Container App after you deploy it. The MCP endpoint you will use will resemble https://*ContainerAppName*.*EnvironmentDomainPrefix*.canadacentral.azurecontainerapps.io/mcp . You will use this MCP endpoint plus the mcp-api-key in a later step.

## Step 2 — Register the MCP Connector on the SRE Agent.

1. Go to your SRE Agent at [sre.azure.com](https://sre.azure.com)
2. Add an MCP server **connector** that contains the following configuration: 

   * **Name**: `health-check-mcp`
   * **Endpoint URL**: {resembles https://*ContainerAppName*.*EnvironmentDomainPrefix*.canadacentral.azurecontainerapps.io/mcp}
   * **Authentication method**: Bearer
   * **API key**: {The value of the mcp-api-key that you added to your Container App}

Verify that the status of the connector shows **Connected** before proceeding to the next steps.

## Step 3 — Register the Subagent

1. In the SRE agent, create a subagent from the contents of the [SubAgent-healthchecker.yaml](SREAgent/service-health-monitor.yaml)
   > Note: Based on the yaml, the name of the subagent that will get created is **service-health-monitor**.
2. Click **Create** → **Subagent**.
3. Switch to the **YAML** tab.
4. Paste the contents of `service-health-monitor.yaml`.
5. Click **Save**.

## Step 4 — Test in Playground

1. In **Subagent builder**, switch to **Test playground**.
2. Select `service-health-monitor` from the dropdown.
3. Here are some sample prompts to try, which you can adjust:

   * `"Check the health of https://httpbin.org/status/200"`
   * `"Batch check these URLs: https://bing.com, https://httpbin.org/status/500, https://example.com"`
   * `"Run a full health check of my Azure App Services and this endpoint {replace with an https endpoint}"`


> Note: The response results include the following JSON: `"custom_flag":"returned by the custom health check MCP server tool"`

## Optional: Wire Up Triggers

### Incident trigger

1. Attach the subagent to a custom incident response plan so that the subagent auto-runs when an alert fires. Sample instruction:

`Run a health check against the impacted resource.`

2. Perform an action that triggers an alert on your resource and triggers the incident response plan. For example, if you are using Azure Monitor as the incident response plan, and you have a Web App with an alert rule that triggers when 3 HTTP 5xxs occur within 5 minutes, trigger three HTTP 500 errors on the Web app.

In turn, the incident response plan should automatically call the service-health-monitor subagent, because the subagent specializes in running health checks.

You can verify that the subagent was invoked by checking the chat (e.g. in an incident alert in SRE Agent), while or after the incident response plan processes the alert.


### Scheduled task

In SRE Agent, create a scheduled tasks to run health checks every 15 minutes:

- **Cron expression:** */15 * * * *
- **Task details (replace REPLACE_WITH_YOUR_SUBSCRIPTION_ID and REPLACE_WITH_YOUR_RESOURCE_GROUP_NAME):** 

```
Perform a full health check cycle. You MUST use the customhealthcheckmcp MCP tools — do NOT use Python code or httpx for health checks.

1. Call customhealthcheckmcp_http_health_check for each Azure web app default hostname in resource group:
   /subscriptions/REPLACE_WITH_YOUR_SUBSCRIPTION_ID/resourceGroups/REPLACE_WITH_YOUR_RESOURCE_GROUP_NAME
   (First run az webapp list to get the hostnames, then probe each with the MCP tool.)

2. Produce a summary status table with columns: Service | Endpoint | Status | Latency | Notes

3. If any endpoint is unhealthy (non-2xx) or latency exceeds 2000ms, flag it and recommend next steps.

4. If all services are healthy, confirm with a brief "All services healthy" summary.
```

After the scheduled task runs, yYou can verify that the subagent was invoked by checking the chat (e.g. in a task run).


