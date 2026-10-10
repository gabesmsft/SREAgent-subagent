# SRE Agent Demo POC: Custom Subagent

A minimal proof-of-concept showing how to use a custom subagent to invoke tools and to be triggered via an incident response plan and scheduled task.

In this demo, we will use a custom subagent that invokes tools on a custom MCP server to do resource health checks.

## Step 1 — Create an SRE Agent

Refer to the [documentation](https://learn.microsoft.com/azure/sre-agent/create-and-set-up#deploy) about how to deploy an SRE Agent.

> Note: You do not need to do the post-deployments steps mentioned in the documentation.

## Step 2 — Deploy an MCP Server

Refer to [this page](https://github.com/azureossd/Container-Apps/tree/main/MCP_server) to deploy an MCP server on a Container App. You will need to deploy the Container App Environment and Container App, but you can deploy each with a button click without having to deploy code or containers. Make note of the mcp-api-key you enter when creating the Container App, and the URL of the Container App after you deploy it. The MCP endpoint you will use will resemble https://*ContainerAppName*.*EnvironmentDomainPrefix*.canadacentral.azurecontainerapps.io/mcp . You will use this MCP endpoint plus the mcp-api-key in a later step.

## Step 3 — Register the MCP Connector on the SRE Agent.

1. Go to your SRE Agent at [sre.azure.com](https://sre.azure.com)
2. Add an MCP server **connector** that contains the following configuration: 

   * **Name**: `health-check-mcp`
   * **Endpoint URL**: {resembles https://*ContainerAppName*.*EnvironmentDomainPrefix*.canadacentral.azurecontainerapps.io/mcp}
   * **Authentication method**: Bearer
   * **API key**: {The value of the mcp-api-key that you added to your Container App}

Verify that the status of the connector shows **Connected** before proceeding to the next steps.

## Step 4 — Create the HTTP Status Parser Tool

Create a custom Python tool named `parse-http-status` from
[`parse_http_status.py`](SREAgent/parse_http_status.py).

This deterministic helper converts an HTTP status code into structured facts,
including the canonical reason phrase, status class, likely failure owner,
retryability, health assessment, and optional latency band. It demonstrates a
skill loading and invoking a custom tool and, through the skill reference in
the custom agent, associative execution of both the skill and tool.

The tool's output should resemble:

```json
{
  "status_code": 503,
  "valid": true,
  "reason_phrase": "Service Unavailable",
  "status_class": "5xx",
  "healthy": false,
  "failure_owner": "server",
  "retryable": true
}
```

The result may also contain `url`, `latency_ms`, and `latency_band` when those
values are supplied.

## Step 5 — Create the HTTP Status Interpretation Skill

Add a skill named `http-status-interpretation` from
[`SKILL.md`](SREAgent/SKILL.md). When creating the skill, select the
`parse-http-status` custom Python tool created in Step 4.

The skill tells the agent to use the parser's structured result as the source
of truth and turn it into a concise operator-facing interpretation. The
expected output format is:

```text
Verdict:  503 Service Unavailable - the service is up but refusing traffic.
Owner:    Server side. Retry is worth attempting; this is usually transient.
Next:     Check instance health and whether a deployment is currently rolling.
```

Seeing this output format after a non-2xx probe verifies that the interpretation
instructions were applied. The corresponding structured status fields in the
execution details verify that the custom Python tool was invoked.

## Step 6 — Register the Subagent

1. In the SRE agent, create a subagent from the contents of [`service-health-monitor.yaml`](SREAgent/service-health-monitor.yaml).
   > Note: Based on the yaml, the name of the subagent that will get created is **service-health-monitor**.
2. Click **Create** → **Subagent**.
3. Switch to the **YAML** tab.
4. Paste the contents of `service-health-monitor.yaml`.
5. Click **Save**.

### Test in Playground

1. In **Subagent builder**, switch to **Test playground**.
2. Select `service-health-monitor` from the dropdown.
3. Here are some sample prompts to try, which you can adjust:

   * `"Check the health of https://httpbin.org/status/200"`
   * `"Batch check these URLs: https://bing.com, https://httpbin.org/status/500, https://example.com"`
   * `"Run a full health check of my Azure App Services and this endpoint {replace with an https endpoint}"`

For a non-2xx result, verify the complete invocation chain by looking for:

- The MCP health-check result includes
  `"custom_flag":"returned by the custom health check MCP server tool"`.
- The Python tool result includes fields such as `status_code`,
  `reason_phrase`, `failure_owner`, and `retryable`.
- The response includes the skill's `Verdict`, `Owner`, and `Next` lines.
- The response ends with:
  `This analysis was brought to you courtesy of the custom healthchecker subagent!`

Together, these signals verify that the MCP tool, custom Python tool, skill,
and custom agent were invoked. The primary end-to-end test can also be run by
triggering an incident response plan associated with the custom agent.

### Test Automatic Handoff

The agent's `handoff_description` allows the main chat experience to select
the custom agent based on the request. To test this routing, send the following
message in chat without using the `/agent` command or explicitly selecting the
custom agent. Replace the placeholders with the Web App and resource group to
test:

```text
Check the health of the <web app name> Web App in the <resource group name> resource group by probing HTTP endpoints and querying Azure Resource Health. Produces status reports with recommendations.
```

Verify that the response contains the custom-agent footer shown above. For a
non-2xx endpoint, also verify the parser fields and the three-line skill output.

### Test Failure Scenarios

Useful failure-mode tests include:

- Stop the remote MCP server to make the connector and associated MCP tools
  unavailable.
- Disable required tools in the portal.
- Disable the `http-status-interpretation` skill.

In each case, confirm that the response reports the unavailable dependency
instead of presenting a successful health assessment.

## Optional: Wire Up Triggers

### Incident trigger

### Create an incident response plan

1. In the SRE Agent, select Azure Monitor as the incident platform (this is default).

2. Create an incident response plan:
   - Include severity 2.
   - Attach the custom agent to the incident response plan.

### Trigger an alert

1. Deploy a Web App via ARM template found [here](https://github.com/gabesmsft/PerfectWebApp), and verify that the page loads successfully.
2. On the SRE Agent, add the Web App's resource group to the list of managed resource groups.

3. On the Web App, do the following:
   a. Change the foo environment variable value from **bark** to **bar**. Based on the web app's code logic, this should start to throw divide by zero exceptions.
   b. Visit the root URL of the Web App at least 3 times within 5 minutes. This should trigger the Azure Monitor alert rule that is configured for the Web App.
   c. After the alert fires, check for an incident in SRE Agent. The incident conversation should show that the health check was run and should show the response from the MCP tool via the service-health-monitor subagent.


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

After the scheduled task runs, you can verify that the subagent was invoked by checking the chat (e.g. in a task run).
