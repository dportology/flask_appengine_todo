# A simple todo list application which is to be ran on google app engine
# Includes authentication with google accounts, and saving of tasks on App Engine's Datastore
#
# This was only meant to be a quick showcase and as such several improvements could be made, including:
#   -Styling (bootstrap)
#   -Separating functionality into separate files (auth logic and routes should be separate)
#   -Non redundant functions - update, delete, and submit share a lot of redundant code
#   -Responsive elements - page just reloads when a task is modified.


from flask import Flask, redirect, render_template, request
from forms import NewTaskForm
import sys
import os
from google.cloud import datastore


# If `entrypoint` is not defined in app.yaml, App Engine will look for an app
# called `app` in `main.py`.
app = Flask(__name__)
app.config['SECRET_KEY'] = '5c41731e9b6f2344d730e528459b2566'

client = datastore.Client()

# Following taken from [https://cloud.google.com/python/getting-started/authenticate-users]  ====================

CERTS = None
AUDIENCE = None

def certs():
    import requests

    global CERTS
    if CERTS is None:
        response = requests.get(
            'https://www.gstatic.com/iap/verify/public_key'
        )
        CERTS = response.json()
    return CERTS

def get_metadata(item_name):
    import requests

    endpoint = 'http://metadata.google.internal'
    path = '/computeMetadata/v1/project/'
    path += item_name
    response = requests.get(
        '{}{}'.format(endpoint, path),
        headers = {'Metadata-Flavor': 'Google'}
    )
    metadata = response.text
    return metadata

def audience():
    global AUDIENCE
    if AUDIENCE is None:
        project_number = get_metadata('numeric-project-id')
        project_id = get_metadata('project-id')
        AUDIENCE = '/projects/{}/apps/{}'.format(
            project_number, project_id
        )
    return AUDIENCE

def validate_assertion(assertion):
    from jose import jwt

    try:
        info = jwt.decode(
            assertion,
            certs(),
            algorithms=['ES256'],
            audience=audience()
            )
        return info['email'], info['sub']
    except Exception as e:
        print('Failed to validate assertion: {}'.format(e), file=sys.stderr)
        return None, None


# ==================================== [end IAP auth ] ====================================

@app.route('/', methods=['GET'])
def hello_world():

    assertion = request.headers.get('X-Goog-Iap-Jwt-Assertion')
    user_email, id = validate_assertion(assertion)

    # https://cloud.google.com/datastore/docs/concepts/queries
    query = client.query(kind='Task')
    query.add_filter('user', '=', user_email)

    query_items = list(query.fetch())
    new_task_form = NewTaskForm()

    return render_template('main.html', name=user_email, tasks=query_items, new_task_form=new_task_form)


@app.route('/logout', methods=['POST'])
def logout():
    """
    YOUR_APP_URL/_gcp_iap/clear_login_cookie
    Redirects user to a special IAP url which clears the cloud IAP login cookie for their session
    See [https://cloud.google.com/iap/docs/special-urls-and-headers-howto] for details
    """
    return redirect('/_gcp_iap/clear_login_cookie')


@app.route('/submit_task', methods=['POST'])
def submit_task():
    """
        Adds new tasks to datastore
    """
    description = request.form['description']  # Form variables
    due_date = request.form['due_date']

    key = client.key('Task')  # Generates datastore key object
    item = datastore.Entity(key)
    assertion = request.headers.get('X-Goog-Iap-Jwt-Assertion')  # Check again for user auth
    user_email, id = validate_assertion(assertion)
    item.update({
        'user':user_email,
        'done': False,
        'description': description,
        'due_date': due_date
    })
    key = client.put(item)

    return redirect('/')  # Puts user back on home page after refresh


@app.route('/update_task', methods=['POST', 'GET'])
def update_task():

    description = request.form['description']  # Form variables
    due_date = request.form['due_date']
    completed = request.form.get('completed_checkbox') != None  # checkboxes work differently for some reason. checking if not None to get a boolean

    assertion = request.headers.get('X-Goog-Iap-Jwt-Assertion') # Check again for user auth
    user_email, id = validate_assertion(assertion)
    task_id = request.args.get('task_id')  # URL param 

    query = client.query(kind='Task')
    # Ideally would query by some other unqiue key for this specific task so I don't have to do the search below
    query.add_filter('user', '=', user_email) 

    items = list(query.fetch())

    for item in items:
        urlsafe = item.key.to_legacy_urlsafe()
        key = datastore.Key.from_legacy_urlsafe(urlsafe)

        if key.id == int(task_id):
            item = datastore.Entity(key)
            item.update({
                'user':user_email,
                'done': completed,
                'description': description,
                'due_date': due_date
            })
            key = client.put(item)

    return redirect('/')  # Puts user back on home page after refresh


@app.route('/delete_task', methods=['POST', 'GET'])
def delete_task():

    assertion = request.headers.get('X-Goog-Iap-Jwt-Assertion')  # Check again for user auth
    user_email, id = validate_assertion(assertion)
    task_id = request.args.get('task_id') # URL param 

    query = client.query(kind='Task')
    # query.add_filter('description', '=', 'test')
    query.add_filter('user', '=', user_email)

    items = list(query.fetch())

    for item in items:
        urlsafe = item.key.to_legacy_urlsafe()
        key = datastore.Key.from_legacy_urlsafe(urlsafe)

        if key.id == int(task_id):
            client.delete(key)

    return redirect('/')  # Puts user back on home page after refresh


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
