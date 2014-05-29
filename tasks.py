from celery import Celery
import model

celery = Celery('tasks')
celery.config_from_object('celeryconfig')


@celery.task
def foo(bar, baz):
    print bar, baz


@celery.task
def search_tweets_text(q, c):
    return model.search_tweets_text(q, c)


@celery.task
def fav(q, c, delay, max_403s):
    model.Favoriter(multiple_q=q, count=c, delay_up_to=delay, max_403s=max_403s).run()
