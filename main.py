from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash,request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user,login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column, Relationship, backref
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# Import your forms from the forms.py
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
import hashlib


'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view="register"

# TODO: Configure Flask-Login

# create a callback function

@login_manager.user_loader
def user_loader(user_id):
    return Users.query.get(int(user_id))


# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# CONFIGURE TABLES
class Blog(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)

    comments:Mapped[list["Comment"]]=Relationship(backref="comment")


# Creating the comment Table
class Comment(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(250), nullable=False)

    blog_id:Mapped[int]=mapped_column(Integer,ForeignKey("blog.id"))
    comment_id:Mapped[int]=mapped_column(Integer,ForeignKey("users.id"))


# TODO: Create a User table for all your registered users. 
class Users(UserMixin,db.Model):
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    email:Mapped[str]=mapped_column(String(250),unique=True,nullable=False)
    password:Mapped[str]=mapped_column(String(250),nullable=False)
    name:Mapped[str]=mapped_column(String(250),nullable=False)

    # "backref" to make poster available as a method in the comment class
    comments:Mapped[list["Comment"]]=Relationship(backref="poster")


with app.app_context():
    db.create_all()



# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=["GET","POST"])
def register():
    form = RegisterForm()
    if request.method=="POST":
        password=request.form.get("password")
        email = request.form.get("email")
        if db.session.execute(db.select(Users).where(Users.email==email)).scalar():
            flash("you've already signed up with that email,login instead")
            return redirect(url_for("login"))
        else:
            password_hash=generate_password_hash(password,method="pbkdf2:sha256",salt_length=8)
            new_user=Users(
                email=email,
                password=password_hash,
                name=request.form.get("name")
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html",form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=["GET","POST"])
def login():
    form=LoginForm()
    if request.method=="POST":
        email=request.form.get("email")
        password=request.form.get("password")
        # check if user's email and password are correct
        try:
            user = db.session.execute(db.select(Users).where(Users.email == email)).scalar()
            password_hash=user.password
            if check_password_hash(password_hash,password):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Invalid Email or Password")
                return redirect(url_for("login",form=form))
        except AttributeError:
            flash("Invalid Email or Password")
            return redirect(url_for("login",form=form))
    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(Blog))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts,logged_in=current_user.is_authenticated,current_user=current_user)






# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>",methods=["GET","POST"])
@login_required
def show_post(post_id):
    form=CommentForm()
    blog_comments=db.session.execute(db.select(Comment).order_by(Comment.id)).scalars().all()
    requested_post = db.get_or_404(Blog, post_id)

    def gravatar_url(email, size=100, default="identicon"):
        email = email.strip().lower().encode("utf-8")
        hash_ = hashlib.md5(email).hexdigest()
        return f"https://www.gravatar.com/avatar/{hash_}?s={size}&d={default}"

    if form.validate_on_submit():
        new_comment=Comment(
            text=form.text.data,
            blog_id=post_id,
            comment_id=current_user.id,
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post",post_id=post_id))

    return render_template("post.html",gravatar_url=gravatar_url,post=requested_post,logged_in=True,form=form,current_user=current_user,blog_comments=blog_comments)

def admin_only(function):
    @wraps(function)
    def wrapper(*args,**kwargs):
        if current_user.id==1:
            return function()
        else:
            return abort(404,description="you don't have the permission to access this requested resource, it is either read protected or protected by the server")
    return wrapper



# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = Blog(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y"),
            # author_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,logged_in=True)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(Blog, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,logged_in=True)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(Blog, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts',logged_in=True))


@app.route("/about")
def about():
    return render_template("about.html",logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html",logged_in=current_user.is_authenticated)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
