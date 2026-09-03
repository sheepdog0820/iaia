from celery import shared_task

from accounts.background_removal_tasks import cleanup_background_removal_jobs as cleanup_jobs


@shared_task(name="accounts.tasks.cleanup_background_removal_jobs")
def cleanup_background_removal_jobs():
    return cleanup_jobs()
