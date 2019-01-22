### Data pipelines for everyone with CRMint
#### Automate your BigQuery SQL queries with this elegant GCP pipeline application.

![](https://cdn-images-1.medium.com/max/800/1*QSxSRgKOzt39wrY19Fa1hg.jpeg)

You’ve been working with Google Cloud for some time, you’ve got data in BigQuery and your confident writing queries to explore it. Maybe you’ve built a couple of reports that use this data, but you’d like them to be automated, so that when you take a day off they still function!

You’re also doing some pretty cool things with this data, pushing it into [Google Analytics](https://analytics.google.com/analytics/web/) so the wider team can benefit from the extra insight, but once again, you’re doing this manually. If you’re out the office the data doesn’t go anywhere — there must be a better way, right?

I was in this situation and unsure where to turn, I read about amazing tools like [Apache Beam](https://beam.apache.org/), [DataFlow](https://cloud.google.com/dataflow/) and [Cloud Composer](https://cloud.google.com/composer/) which seemed to do exactly what I wanted, but as I started to explore them the learning curve was steep, and they seemed to be providing large solutions to a relatively small problem.

All I wanted to do was run some SQL automatically and move my data around, is there not an elegant tool that can do just this?

#### Enter CRMint

CRMint is a Google App Engine application built by a team within Google, which they have kindly open sourced. Following the documentation I was able to get the CRMint app up and running on Google Cloud in no time at all, and I’ve been using it to run data pipelines every day since.

![](https://cdn-images-1.medium.com/max/800/1*y2DPw-ObK8L6mjPpAJd_RQ.jpeg)

To quote directly from the [CRMint GitHub page](https://github.com/google/crmint/)…

> CRMint was created to make advertisers’ data integration and processing easy, even for people without software engineering background.

> CRMint has simple and intuitive web UI that allows users to create, edit, run, and schedule data pipelines consisting of data transfer and data processing jobs.

### CRMint in practice

So what exactly can CRMint do? CRMint is a pipeline application designed to make the process of simple automation and moving of data as simple as possible. Here are a handful of the jobs you can perform with this lightweight pipeline application:

-   Run SQL queries in BigQuery to rebuild tables or aggregate data.
-   Export data from BigQuery to Google Cloud Storage.
-   Import data into Google Analytics.
-   Send data to a Google Cloud ML model for predictions.

#### Let’s run through an example pipeline…

Once you’ve got CRMint installed you’ll see a screen similar to the one below:

![](https://cdn-images-1.medium.com/max/800/1*8iCuIMt0aqk5jXAnhmblHw.jpeg)

Let’s start by clicking on the ‘**New Pipeline**’ button.

![](https://cdn-images-1.medium.com/max/800/1*7ijy4_XT8UXZwy0lr2WjNg.jpeg)

We can give our new pipeline a name, set an email address to receive notifications when it completes successfully (or if something goes wrong!), set a schedule for it and define some pipeline level variables (both of which we’ll come back to later).

Once created, we’ll have an empty pipeline, shown as a blank canvas ready to be filled with our jobs!

![](https://cdn-images-1.medium.com/max/800/1*CvqCAF8BdRDDTQSFfCA16Q.png)

#### Creating our first job

Now we’ll click onto ‘**Create New Job**’ to add our first task to this pipeline. Doing so displays the job creation screen. The first thing to call out on here is the ‘**Worker Class**’, where you select the worker appropriate to the job you want to do. CRMint has several built in workers that perform different tasks, such as sending data to Google Cloud Storage, running a query in BigQuery or sending data to Google Analytics.

![](https://cdn-images-1.medium.com/max/800/1*YolaYs9nWS6PRfVJb3pMXw.jpeg)

In the example below I’ve added a simple BigQuery job and entered my SQL into the ‘query’ box provided. The next step is to provide the dataset ID and table name, which CRMint will use as it’s destination for this query, appending or overwriting on completion.

![](https://cdn-images-1.medium.com/max/800/1*Cxj7mtWpCIEA1AshdfoACA.jpeg)

#### Job dependencies

You’ll also notice a ‘Job Dependencies’ section, another excellent feature of CRMint. The concept of a pipeline is that you need things to happen in a particular order, perhaps you need to aggregate some data before you write it out, or perform another calculation on it.

Dependencies will make this magic happen. Simply add rules for each job that tell it to only start when it’s preceding jobs have been successful — or even if they fail, depending on your choice!

![](https://cdn-images-1.medium.com/max/800/1*H9QRijIAP8tlpFICcTaERA.jpeg)

As you start to add more jobs and dependencies between them you’ll see your pipeline start to grow. When you’re ready to take it for a spin, click on the ‘**Run Pipeline**’ button in the top right and you’ll see your jobs run, starting at the top and running down according to their dependencies, until the whole pipeline completes, or encounters an error.

![](https://cdn-images-1.medium.com/max/800/1*e81Uu2_xeRw6t3fh6rfiUQ.jpeg)

If every job completes successfully you’ll see the button below, next to your pipeline, and all it’s individual jobs will show with a green tick!

![](https://cdn-images-1.medium.com/max/800/1*BYCyayE4v9pg9TH1Zpo5jg.png)

#### Oops?

If you hit a snag here, there is an excellent ‘logs’ tab in each pipeline that gives detail on the errors for failed jobs, as well as more detailed information on successful ones.

![](https://cdn-images-1.medium.com/max/800/1*XtWHGeXH0B1RjSXUmwgiEQ.jpeg)

#### Schedules

Okay, so have your pipeline built, you’ve tested it and it works great. Remember we wanted to automate our process, so that when we take a day off our colleagues reports will still be updated with beautiful fresh data — CRMint makes it simple to schedule your pipeline.

Clicking on the ‘**Edit**’ button of your pipeline shows the screen you saw when you first created it. You can rename your pipeline, set an email for alerts and set schedules:

![](https://cdn-images-1.medium.com/max/800/1*1nZzAszBAbQPDnfuYoX4fQ.jpeg)

Schedules use [CRON formatting](https://en.wikipedia.org/wiki/Cron), in the example above our pipeline will run **every day at 9am**. You can select the checkbox to activate this schedule, or alternatively there is a slider which you can toggle on the pipeline visualization page, which will activate any schedule you have defined in the settings.

#### Setting variables

The penultimate feature I’d like to mention is the ability to set variables. These can be pipeline level (only defined for a single pipeline) or global (callable across any pipeline you create). Variables let you parameterize your queries, saving repetitive code and allowing you to easily change the scope of your queries when required.

For example, we could set a query for the number of day’s worth of data we want to query (as below) then easily call the value of this variable in our code using **{% NUMBER_OF_DAYS %}**.

This is a simple example, but if your using a single value over several queries and want a way to easily update it, variables are going to save you a lot of time!

![](https://cdn-images-1.medium.com/max/800/1*KRREBjCWr7OoOMHhKSAnJg.png)

#### Inline functions

As well as custom variables, there are a handful of functions built into the core of CRMint that you may find helpful.

For example **{% today(‘%Y-%m-%d’) %}** will insert today’s date in the YYYY-MM-DD format. You can use these functions in your query or in any of the destination fields; great if you want your query to write out to a different table every day, or perhaps to a .csv file on Google Cloud Storage with a unique name every day.

Here are a couple more example of inline functions in action:

-   **my_file_{% day_ago(3, ‘%Y-%m-%d’) %}.csv  
    **will evaluate to the string ‘my_file_2018–11–11.csv’, inserting the date as of 3 days ago.
-   **my_file_{% hours_ago(10, ‘%Y-%m-%d_%H-%M’) %}.csv  
    **will evaluate to the string ‘my_file_2018–11–14_10–06.csv’, inserting the time as of 10 hours ago.

#### Conclusion

This concludes my short introduction to CRMint, there are many more features and workers that don’t fit into the scope of this introduction, and more are being added all the time.

If you have questions about anything I’ve not covered feel free to leave a comment below and I will try my best to answer.

If any of the above sounds familiar or useful to your working process then I encourage you to [check out CRMint on Github](https://github.com/google/crmint) and start building out your own data pipelines today!
