from wtforms import Form, StringField, PasswordField, validators, HiddenField

class LoginForm(Form):
    url = StringField('url', [validators.Required()])
    username = StringField('username', [validators.Required()])
    password = PasswordField('password', [validators.Required()])


