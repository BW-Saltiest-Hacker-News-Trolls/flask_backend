import csv
from decouple import config
import json
from flask import Flask, jsonify
import pandas as pd
import sqlite3
from sqlalchemy import func

from .models import DB, Comment
from .make_dummies import dummy_output, dummy_user_output
from .load_comments import load_from_csv, insert_comment


    

def create_app():
    app = Flask(__name__)
    app.config['ENV'] = config('ENV')
    app.config['SQLALCHEMY_DATABASE_URI'] = config('DATABASE_URL')
    DB.init_app(app)

    @app.route('/')
    def index():
        return "...hello."

    @app.route('/dbload')
    def dbload():
        """loads HackerNews data from a local .csv file."""
        data = load_from_csv()
        for d in data:
            insert_comment(d)
        DB.session.commit()
        return "loaded!"

    @app.route('/smallload')
    def smallload():
        """loads 50 rows of HackerNews data from a local .csv file."""
        data = load_from_csv()
        for i in range(0,50):
            insert_comment(data[i])
        DB.session.commit()
        return "small loaded!"

    @app.route('/feed')
    def feed():
        """returns a JSON of all the comments in the database."""
        comment_objs = Comment.query.all()
        comments = [tuple([obj.comment_id, obj.text, obj.author, obj.toxicity]) for obj in comment_objs]
        comments = [dict(zip(tuple(['id','text','author','tox']),obj)) for obj in comments]

        return jsonify(comments)

    @app.route('/author/<username>')
    def author(username):
        """returns a JSON containing a comment author's average and total toxicity score, their toxicity rank,
        and their ten most toxic comments."""
        comment_objs = Comment.query.filter(Comment.author == username).order_by(Comment.toxicity.desc()).limit(10)
        comments = [tuple([obj.comment_id, obj.text, obj.toxicity]) for obj in comment_objs]
        comments = [dict(zip(tuple(['id','text','tox']),obj)) for obj in comments]

        total = Comment.query.with_entities(
             func.sum(Comment.toxicity).label("Sum")
         ).filter_by(
             author=username
         ).first()

        avg = Comment.query.with_entities(
             func.avg(Comment.toxicity).label("Avg")
         ).filter_by(
             author=username
         ).first()

        toxrank_result = DB.session.execute(f"""SELECT tox_rank FROM (
        SELECT author, mean,  RANK () OVER (ORDER BY mean DESC) as tox_rank FROM (
        SELECT author, AVG(toxicity) as mean FROM comment GROUP BY author) AS mean_toxes) AS tox_ranks WHERE author = '{username}';""")
        toxrank_rows = [x for x in toxrank_result]
        toxrank = [x.items() for x in toxrank_rows][0][0][1]

        return jsonify(dict(zip(tuple(['username','avg_tox','total_tox','tox_rank','top_ten_tox']),
        tuple([username,float(avg.Avg),float(total.Sum),int(toxrank),comments]))))


    @app.route('/reset')
    def reset():
        """resets the database."""
        DB.drop_all()
        DB.create_all()
        return "database reset."


    return app