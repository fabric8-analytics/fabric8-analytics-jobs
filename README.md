# Bayesian core Jobs service

The aim of this service is to provide a single configuration point for Bayesian core periodic tasks or more sophisticated analyses execution (jobs).

## Job

A job is an abstraction in Bayesian core that allows one to manipulate with core workers with more granted semantics. An example of a job can be scheduling all analyses that failed, scheduling analyses of new releases, etc.

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

Bayesian job service can go down. As jobs are stored in the database (PostgreSQL), jobs are not lost. However some jobs could be possibly executed during the service unavailability. Misfire grace time is taken in account when the job service goes up again - if there would be some jobs scheduled during the service unavailability, misfire grace time tells scheduler whether these jobs should be run - if scheduled time plus misfire grace time is less then the current time.

## Default jobs

Default jobs can be found in `baysian_jobs/default_jobs/` directory. These jobs are described in a YAML file (one file per job definition). The configuration keys stated in YAML files conform to job options as described above. Required are `job_id` (to avoid job duplication since these jobs are added each time on start up), `kwargs` and `handler`. If some configuration options are not stated, they default to values as in section above. Browse `bayesian_jobs/default_jobs/` directory for examples.

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
curl -X POST --header 'Content-Type: application/json' --header 'Accept: application/json' -d '{ \ 
   "flow_arguments": [ \ 
     { \ 
       "ecosystem": "npm", \ 
       "force": true, \ 
       "name": "serve-static", \ 
       "version": "1.7.1" \ 
     }, \ 
     { \ 
       "ecosystem": "maven", \ 
       "force": true, \ 
       "name": "net.iharder:base64", \ 
       "version": "2.3.9" \ 
     } \ 
   ], \ 
   "flow_name": "bayesianFlow" \ 
 }' 'http://localhost:34000/api/v1/jobs/flow-scheduling?state=running'
```

If something went wrong, check failed jobs in "Jobs options", `/jobs` endpoint. There are tracked failed jobs with all the details such as exceptions that were raised, see bellow.

## Job failures

If a job fails, there is inserted a log entry to database. This entry is basically an empty job (when run it does nothing) with information that describe failure (traceback) and job arguments.

## Implementing a job
 
In order to implement a job, follow these steps:

  1. Add your job handler to `bayesian_jobs/handlers/` module. This handler has to be a class that derives from `bayesian_jobs.handlers.BaseHandler`. Implement `execute()` method and give it arguments you would like to get from API calls or YAML configuration file.
  2. Introduce API endpoint and handler-specific POST entry to `bayesian_jobs/swagger.yaml` with an example of `kwargs`. Check already existing entries as an example.
  3. Add function (`operationId`) to `bayesian_jobs/api_v1.py` that will translate API call to `post_schedule_job`. See examples for more info (see section `Handler specific POST requests` in the source code).
  4. Use your job handler.
  
  
Note: Do not try to automatize/remove step 3. It is not possible to do something like `partial` or `__call__` to class as Connexion is checking file existence. Function for each API endpoint has to be unique and it *really has to be* a function. 
 
## See Also

[Connexion](https://github.com/zalando/connexion) - framework used for YAML configuration of API endpoints for Flask
[apscheduler](http://apscheduler.readthedocs.io/en/latest/) - Advanced Python Scheduler used for scheduling jobs (and job's persistence)
