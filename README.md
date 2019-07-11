[![Build Status](https://ci.centos.org/buildStatus/icon?job=devtools-fabric8-analytics-jobs-f8a-build-master)](https://ci.centos.org/job/devtools-fabric8-analytics-jobs-f8a-build-master/)

# Fabric8-Analytics core Jobs service

The aim of this service is to provide a single configuration point for Fabric8-Analytics core periodic tasks or more sophisticated analyses execution (jobs).

## Contributing

See our [contributing guidelines](https://github.com/fabric8-analytics/common/blob/master/CONTRIBUTING.md) for more info.
 
## Job

A job is an abstraction in Fabric8-Analytics core that allows one to manipulate with core workers with more granted semantics. An example of a job can be scheduling all analyses that failed, scheduling analyses of new releases, etc.

A job can be run periodically (periodic jobs) or once in the given time (one-shot jobs). All parameters that can be supplied to a job:

 * `job_id` - a unique string (job identifier) to reference and manipulate with the given job, there is generated a job id if it was omitted on job creation
 * `periodically` - a string that defines whether the job should be run periodically (if omitted the job is run only once (based on `when`, see bellow); examples:
   * "1 week" - run job once a week
   * "5:00:00" - run job once in 5 hours
 * `when` - a starting datetime when should be job executed for the first time, if omitted job is scheduled for the current time *ALL TIMES ARE IN UTC!*
   * Mon Feb 20, 14:56
 * `misfire_grace_time` - time that describes allowed delay of job’s execution before the job is thrown away (for more info see bellow)
 * `state` - job state
   * paused - the job execution is paused/postponed
   * running - job is active and ready for execution
   * pending - job is being scheduled
 * `kwargs` - keyword arguments as supplied to job handler (see Implementing a job section).
 

### Misfire grace time

Fabric8-Analytics job service can go down. As jobs are stored in the database (PostgreSQL), jobs are not lost. However some jobs could be possibly executed during the service unavailability. Misfire grace time is taken in account when the job service goes up again - if there would be some jobs scheduled during the service unavailability, misfire grace time tells scheduler whether these jobs should be run - if scheduled time plus misfire grace time is less then the current time.

## Default jobs

Default jobs can be found in `f8a_jobs/default_jobs/` directory. These jobs are described in a YAML file (one file per job definition). The configuration keys stated in YAML files conform to job options as described above. Required are `job_id` (to avoid job duplication since these jobs are added each time on start up), `kwargs` and `handler`. If some configuration options are not stated, they default to values as in section above. Browse `f8a_jobs/default_jobs/` directory for examples.

## Adding a new job

A new job can be added by:

  * doing request to API - once the database will be erased, these jobs will disappear
  * specifying job in a YAML file - these jobs are inserted to database on each start up (duplicities are avoided)

### Running a custom job

You can use UI that will automatically create periodic jobs, do POST requests for you or generate curl commands that can be run. Just go to the `/api/v1/ui/` endpoint and:

  1. click on "Add new jobs"
  2. Select desired action, for analyses scheduling click on "POST /jobs/flow-scheduling"
  3. Modify job parameters if needed
     * ! Make sure you create a job with a state you want - `running` or `paused`
  4. Follow example arguments - you can click on the example on the right hand side and modify it as desired
  5. Click on "Try it out!", the flow will be scheduled
  
The UI will also prepare a curl command for you. Here is an example for analyses scheduling for two packages (localhost):

```bash
curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' -d '{ 
   "flow_arguments": [ 
     { 
       "ecosystem": "npm", 
       "force": true, 
       "name": "serve-static", 
       "version": "1.7.1" 
     }, 
     { 
       "ecosystem": "maven", 
       "force": true, 
       "name": "net.iharder:base64", 
       "version": "2.3.9" 
     } 
   ], 
   "flow_name": "bayesianFlow" 
 }' 'http://localhost:34000/api/v1/jobs/flow-scheduling?state=running'
```

If something went wrong, check failed jobs in "Jobs options", `/jobs` endpoint. There are tracked failed jobs with all the details such as exceptions that were raised, see bellow.

## Job failures

If a job fails, there is inserted a log entry to database. This entry is basically an empty job (when run it does nothing) with information that describe failure (trace back) and job arguments.

## Implementing a job
 
In order to implement a job, follow these steps:

  1. Add your job handler to `f8a_jobs/handlers/` module. This handler has to be a class that derives from `f8a_jobs.handlers.BaseHandler`. Implement `execute()` method and give it arguments you would like to get from API calls or YAML configuration file.
  2. Introduce API endpoint and handler-specific POST entry to `f8a_jobs/swagger.yaml` with an example of `kwargs`. Check already existing entries as an example.
  3. Add function (`operationId`) to `f8a_jobs/api_v1.py` that will translate API call to `post_schedule_job`. See examples for more info (see section `Handler specific POST requests` in the source code).
  4. Use your job handler.
  
  
Note: Do not try to automatize/remove step 3. It is not possible to do something like `partial` or `__call__` to class as Connexion is checking file existence. Function for each API endpoint has to be unique and it *really has to be* a function. 


# Prepared queries that might be useful

The list bellow states examples of filter queries not specific to any flow. An example of usage could be an HTTP POST request to `/api/v1/jobs/flow-scheduling` for flow scheduling with appropriate parameters (see the `curl` example above):

```json
{
  "flow_arguments": [
    { 
      "$filter": "YOUR-FILTER-QUERY-GOES-HERE"
    }
  ],
  "flow_name": "bayesianFlow"
}
```

If you wish to schedule only certain tasks in flows, feel free to post your HTTP POST request to `/api/v1/jobs/flow-scheduling` endpoint:
```json
{
  "flow_arguments": [
    { 
      "$filter": "YOUR-FILTER-QUERY-GOES-HERE"
    }
  ],
  "flow_name": "bayesianFlow",
  "run_subsequent": false,
  "task_names": [
    "github_details",
    "ResultCollector"
  ]
}
````

## Run graph syncs of previously analyzed Ecosystem-Package-Version

Note this represents the whole job arguments in which there are only first 1000 packages synced, post this to `/api/v1/jobs/selective-flow-scheduling` endpoint.

```json
{
  "flow_arguments": [
    {
      "force": true,
      "$filter": {
        "joins": [
          {
            "on": {
              "analyses.id": "versions.id"
            },
            "table": "versions"
          },
          {
            "on": {
              "versions.package_id": "packages.id"
            },
            "table": "packages"
          },
          {
            "on": {
              "ecosystems.id": "packages.ecosystem_id"
            },
            "table": "ecosystems"
          }
        ],
        "limit": 1000,
        "table": "analyses",
        "order_by": "analyses.id desc",
        "select": [
          "versions.identifier as version",
          "packages.name as name",
          "ecosystems.name as ecosystem"
        ],
        "where": {
          "analyses.id in": {
            "$filter": {
              "joins": [
                {
                  "on": {
                    "worker_results.analysis_id": "analyses.id"
                  },
                  "table": "analyses"
                },
                {
                  "on": {
                    "analyses.id": "versions.id"
                  },
                  "table": "versions"
                },
                {
                  "on": {
                    "versions.package_id": "packages.id"
                  },
                  "table": "packages"
                },
                {
                  "on": {
                    "ecosystems.id": "packages.ecosystem_id"
                  },
                  "table": "ecosystems"
                }
              ],
              "table": "worker_results",
              "select": [
                "analyses.id as analyses_id"
              ],
              "distinct": true,
              "where": {
                "analyses.finished_at is not": null
              }
            }
          }
        }
      }
    }
  ],
  "flow_name": "bayesianFlow",
  "run_subsequent": false,
  "task_names": [
    "GraphImporterTask"
  ]
}
```

## Force run all analyses which failed

```json
{
  "$filter": {
    "joins": [
      {
        "on": {
          "worker_results.analysis_id": "analyses.id"
        },
        "table": "analyses"
      },
      {
        "on": {
          "analyses.id": "versions.id"
        },
        "table": "versions"
      },
      {
        "on": {
          "versions.package_id": "packages.id"
        },
        "table": "packages"
      },
      {
        "on": {
          "ecosystems.id": "packages.ecosystem_id"
        },
        "table": "ecosystems"
      }
    ],
    "select": [
      "packages.name as name",
      "ecosystems.name as ecosystem",
      "versions.identifier as version"
    ],
    "table": "worker_results",
    "where": {
      "worker_results.error": true
    }
  },
  "force": true
}
```

## Force analyses that started at some date

```json
{
  "$filter": {
    "joins": [
      {
        "on": {
          "analyses.id": "versions.id"
        },
        "table": "versions"
      },
      {
        "on": {
          "versions.package_id": "packages.id"
        },
        "table": "packages"
      },
      {
        "on": {
          "ecosystems.id": "packages.ecosystem_id"
        },
        "table": "ecosystems"
      }
    ],
    "select": [
      "packages.name as name",
      "ecosystems.name as ecosystem",
      "versions.identifier as version"
    ],
    "table": "analyses",
    "where": {
      "analyses.started_at >": "2017-04-01 20:00:00"
    }
  },
  "force": true
}
```

## Force analyses which did not finish:

Note that this schedules analyses that are in progress.

```json
{
  "$filter": {
    "joins": [
      {
        "on": {
          "analyses.id": "versions.id"
        },
        "table": "versions"
      },
      {
        "on": {
          "versions.package_id": "packages.id"
        },
        "table": "packages"
      },
      {
        "on": {
          "ecosystems.id": "packages.ecosystem_id"
        },
        "table": "ecosystems"
      }
    ],
    "select": [
      "packages.name as name",
      "ecosystems.name as ecosystem",
      "versions.identifier as version"
    ],
    "table": "analyses",
    "where": {
      "analyses.finished_at": null
    }
  },
  "force": true
}
```

## Number of analyses in database

```json
{
  "$filter": {
    "table": "analyses",
    "count": true
  }
}
```

## Schedule all analyses that have `finished_at` NULL and there is no newer successful analysis for the given EPV

```json
{
  "force": true,
  "$filter": {
    "joins": [
      {
        "on": {
          "A.version_id": "versions.id"
        },
        "type": "left",
        "table": "versions"
      },
      {
        "on": {
          "versions.package_id": "packages.id"
        },
        "type": "left",
        "table": "packages"
      },
      {
        "on": {
          "packages.ecosystem_id": "ecosystems.id"
        },
        "type": "left",
        "table": "ecosystems"
      }
    ],
    "select": [
      "versions.identifier as version",
      "packages.name as name",
      "ecosystems.name as ecosystem",
    ],
    "table": "analyses AS A",
    "distinct": true,
    "where": {
      "A.finished_at is": null,
      "versions.id not in": {
        "$filter": {
          "joins": [
            {
              "on": {
                "analyses.version_id": "versions.id"
              },
              "type": "left",
              "table": "versions"
            }
          ],
          "table": "analyses",
          "select": "versions.id",
          "where": {"analyses.finished_at is not": null, "analyses.started_at >": "$A.started_at"}
        }
      }
    }
  }
}
```

Translated into:
```sql
SELECT DISTINCT "versions"."identifier" AS "version", "packages"."name" AS "name", "ecosystems"."name" AS "ecosystem", "versions"."id" AS "version_id" FROM "analyses" AS "A" LEFT JOIN "versions" ON "A"."version_id" = "versions"."id" LEFT JOIN "packages" ON "versions"."package_id" = "packages"."id" LEFT JOIN "ecosystems" ON "packages"."ecosystem_id" = "ecosystems"."id" WHERE "versions"."id" NOT IN ( SELECT "versions"."id" FROM "analyses" LEFT JOIN "versions" ON "analyses"."version_id" = "versions"."id" WHERE "analyses"."finished_at" IS NOT NULL AND "analyses"."started_at" > "A"."started_at" ) AND "A"."finished_at" IS NULL
```


## Notes to filter queries

All queries listed above select ecosystem/package/version triplet as most flows expect these to be present as flow arguments. Feel free to modify the select statement if necessary.

Nested queries are supported. Just state nested "$filter".

If you wish to try your query, feel free to POST your query to `/api/v1/debug-expand-filter` to see what results you get with your query or `/api/v1/debug-show-select-query` to see how the JSON is translated into an SQL expression.

If you need any help, contact Fridolin. Also if you find some query useful, feel free to open a PR.

# Authentication & Authorization

If the jobs service is running in production environment, there needs to be done authentication in order to manipulate with endpoints. Jobs service authenticates users against Github OAuth which provides you a token that you can use to do post requests.

You can generate token by accessing `/api/v1/generate-token` endpoint. It will redirect you to Github, which will ask for access to your account info in order to verify that you are a member of Github organization. Once you grant the access, you will be redirected back to Jobs service, which gives you information about your current token.

Note that if you are using Swagger UI, you cannot use this UI for generating endpoints as Swagger does not follow redirects.

Once you are authorized, use your token to access application endpoints - it is expected to state token in `AUTH-TOKEN` header. If you are using Swagger UI, press the `Authorize` button in the header bar and place your token there. After that Swagger UI will transparently use your token for authorization. Note that Swagger UI is client-side application - it constructs requests in your browser so you have to do these steps manually.

If you want to logout, just access `/api/v1/logout` endpoint, which will remove active token from the current session.

To get info about the current session, access `/api/v1/authorized` endpoint.

If you cannot authenticate, please make sure you are a member of fabric8-analytics organization on GitHub. If you are still getting authentication errors, try to [switch from private organization member to public organization member](https://help.github.com/articles/publicizing-or-hiding-organization-membership/).


# Collecting and processing manifest files from GitHub

There are two jobs that can be used to collect and process manifest files from GitHub. The first one is called `jobs/github-manifests`. This job collects and processes manifest files from given GitHub repositories. Example usage:

```shell
curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' --header 'auth-token: <your-token-here>' -d '{
   "repositories": [
     {
       "ecosystem": "maven",
       "force": true,
       "force_graph_sync": false,
       "recursive_limit": 0,
       "repo_name": "omalley/base64"
     }
   ]
 }' 'http://bayesian-jobs-bayesian-production.09b5.dsaas.openshiftapps.com/api/v1/jobs/github-manifests?state=running&skip_if_exists=true'
```

The command above will collect manifest files from https://github.com/omalley/base64 and analyze dependencies found in those manifest files.

It's possible to later aggregate package names from already analyzed manifest files. It can be achieved with a job called `jobs/aggregate-github-manifest-pkgs`. Example usage:


```shell
curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' --header 'auth-token: <your-token-here>' -d '{
   "repositories": [
     {
       "ecosystem": "maven",
       "repo_name": "omalley/base64"
     }
   ]
 }' 'http://bayesian-jobs-bayesian-production.09b5.dsaas.openshiftapps.com/api/v1/jobs/aggregate-github-manifest-pkgs?state=running&bucket_name=my-bucket&object_key=packages_list.json&ecosystem=maven'
```

The command above will aggregate package names from manifest files found in given repositories and store them in `packages_list.json` object in `my-bucket` S3 bucket.


Note both jobs require [authentication](#authentication-authorization).


## See Also

[Connexion](https://github.com/zalando/connexion) - framework used for YAML configuration of API endpoints for Flask
[apscheduler](http://apscheduler.readthedocs.io/en/latest/) - Advanced Python Scheduler used for scheduling jobs (and job's persistence)

### Footnotes

#### Coding standards

- You can use scripts `run-linter.sh` and `check-docstyle.sh` to check if the code follows [PEP 8](https://www.python.org/dev/peps/pep-0008/) and [PEP 257](https://www.python.org/dev/peps/pep-0257/) coding standards. These scripts can be run w/o any arguments:

```
./run-linter.sh
./check-docstyle.sh
```

The first script checks the indentation, line lengths, variable names, white space around operators etc. The second
script checks all documentation strings - its presence and format. Please fix any warnings and errors reported by these
scripts.

List of directories containing source code, that needs to be checked, are stored in a file `directories.txt`

#### Code complexity measurement

The scripts `measure-cyclomatic-complexity.sh` and `measure-maintainability-index.sh` are used to measure code complexity. These scripts can be run w/o any arguments:

```
./measure-cyclomatic-complexity.sh
./measure-maintainability-index.sh
```

The first script measures cyclomatic complexity of all Python sources found in the repository. Please see [this table](https://radon.readthedocs.io/en/latest/commandline.html#the-cc-command) for further explanation on how to comprehend the results.

The second script measures maintainability index of all Python sources found in the repository. Please see [the following link](https://radon.readthedocs.io/en/latest/commandline.html#the-mi-command) with explanation of this measurement.

You can specify command line option `--fail-on-error` if you need to check and use the exit code in your workflow. In this case the script returns 0 when no failures has been found and non zero value instead.

#### Dead code detection

The script `detect-dead-code.sh` can be used to detect dead code in the repository. This script can be run w/o any arguments:

```
./detect-dead-code.sh
```

Please note that due to Python's dynamic nature, static code analyzers are likely to miss some dead code. Also, code that is only called implicitly may be reported as unused.

Because of this potential problems, only code detected with more than 90% of confidence is reported.

List of directories containing source code, that needs to be checked, are stored in a file `directories.txt`

#### Common issues detection

The script `detect-common-errors.sh` can be used to detect common errors in the repository. This script can be run w/o any arguments:

```
./detect-common-errors.sh
```

Please note that only semantical problems are reported.

List of directories containing source code, that needs to be checked, are stored in a file `directories.txt`

#### Check for scripts written in BASH

The script named `check-bashscripts.sh` can be used to check all BASH scripts (in fact: all files with the `.sh` extension) for various possible issues, incompatibilities, and caveats. This script can be run w/o any arguments:

```
./check-bashscripts.sh
```

Please see [the following link](https://github.com/koalaman/shellcheck) for further explanation, how the ShellCheck works and which issues can be detected.
