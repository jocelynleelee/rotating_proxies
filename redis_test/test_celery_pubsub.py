import celery
import celery_pubsub

@celery.shared_task
def my_task_1(*args, **kwargs):
    return "task 1 done"


@celery.shared_task
def my_task_2(*args, **kwargs):
    return "task 2 done"


# First, let's subscribe
celery_pubsub.subscribe('some.topic', my_task_1)
celery_pubsub.subscribe('some.topic', my_task_2)

# Or subscribe with decorator + task decorator
@celery_pubsub.subscribe_to(topic="some.topic")
@celery.shared_task
def my_task_3(*args, **kwargs):
    return "task 3 done"

# Or use only `subscribe_to` decorator
@celery_pubsub.subscribe_to(topic="some.topic")
def my_task_4(*args, **kwargs):
    return "task 4 done"

# Now, let's publish something
res = celery_pubsub.publish('some.topic', data='something', value=42)

# We can get the results if we want to (and if the tasks returned something)
# But in pub/sub, usually, there's no result.
print(res.get())

# This will get nowhere, as no task subscribed to this topic
res = celery_pubsub.publish('nowhere', data='something else', value=23)