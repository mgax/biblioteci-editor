import logging
import re
import requests
import flask

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
GITHUB_URL = 'https://api.github.com/repos/'


class RepoClient(object):

    def __init__(self, repo, token):
        self.repo = repo
        self.token = token

    def _request(self, method, resource, data, headers):
        url = GITHUB_URL + self.repo + '/' + resource
        headers = dict(headers, Authorization='token ' + self.token)
        kwargs = {'headers': headers}
        if data is not None:
            kwargs['data'] = flask.json.dumps(data)
        resp = requests.request(method, url, **kwargs)
        if resp.status_code >= 400:
            logger.info("GitHub API error: %r", resp.json())
            raise RuntimeError("API error")
        self.rate_limit_remaining = resp.headers['X-RateLimit-Remaining']
        return resp.json()

    def get(self, resource, headers={}):
        return self._request('GET', resource, None, headers)

    def post(self, resource, data, headers={}):
        return self._request('POST', resource, data, headers)

    def patch(self, resource, data, headers={}):
        return self._request('PATCH', resource, data, headers)


def _setup():
    config = flask.current_app.config
    m = re.match(r'^(.*)@(.*):(.*)$', config['GITHUB_FILE'])
    (repo, branch, path) = m.group(1, 2, 3)
    api = RepoClient(repo, config['GITHUB_TOKEN'])
    return api, branch, path


def commit(data, message):
    api, branch, path = _setup()
    base = api.get('git/refs/heads/' + branch)['object']['sha']
    base_tree = api.get('git/commits/' + base)['tree']['sha']
    data_json = flask.json.dumps(data, indent=4, sort_keys=True)
    tree_data = {
        'base_tree': base_tree,
        'tree': [{'path': path, 'content': data_json, 'mode': '100644'}],
    }
    tree = api.post('git/trees', tree_data)['sha']
    commit_data = {'parents': [base], 'tree': tree, 'message': message}
    commit = api.post('git/commits', commit_data)['sha']
    api.patch('git/refs/heads/' + branch, {'sha': commit})
    logger.info("Rate limit remaining: %s", api.rate_limit_remaining)


def get_data():
    api, branch, path = _setup()
    commit = api.get('git/refs/heads/' + branch)['object']['sha']
    tree = api.get('git/commits/' + commit)['tree']['sha']
    file_list = api.get('git/trees/' + tree + '?recursive=1')['tree']
    file_map = {f['path']: f['sha'] for f in file_list}
    accept_header = {'Accept': 'application/vnd.github.v3.raw'}
    data = api.get('git/blobs/' + file_map[path], headers=accept_header)
    logger.info("Rate limit remaining: %s", api.rate_limit_remaining)
    return data
