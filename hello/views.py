import logging

from gettingstarted import settings
from django.utils.html import escape
from django.shortcuts import render, redirect
from tweepy import TweepError, API, OAuthHandler

from hello.forms import ReportForm


def index(request):
    form = ReportForm
    if 'denied' in request.GET.keys():
        return render(request, "index.html", {"form": form, "info": "Unauthorized"})

    if 'oauth_token' in request.GET.keys() and \
            'oauth_verifier' in request.GET.keys() and \
            request.session.get('request_token', None) is not None and \
            request.session.get('form_value', None) is not None:
        request_token = request.session.pop('request_token')
        oauth_token = request.GET['oauth_token']
        if oauth_token != request_token:
            return render(request, "index.html", {"form": form, "info": "Failed to authenticate using Twitter"})
        oauth_verifier = request.GET['oauth_verifier']
        accounts = parse_input(request.session.get('form_value'))
        output = do_report(request_token, oauth_verifier, accounts)
        return render(request, "index.html", {"form": form, "output": output})
    else:
        return render(request, "index.html", {"form": form})


def parse_input(accounts):
    values = {}
    accounts = accounts.split('\n')
    for account in accounts:
        account = account.replace('\r', '')
        account = account.replace('@', '')
        account = account.replace('https://twitter.com/', '')
        account = account.replace('https://mobile.twitter.com/', '')
        if account.isdigit():
            values[account] = 'user_id'
        else:
            length = len(account)
            if 4 < length < 51:  # skip anything with different length
                values[account] = 'screen_name'
    return values


def report(request):
    twitter_auth = OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
    authorization_url = twitter_auth.get_authorization_url()
    request.session['request_token'] = twitter_auth.request_token['oauth_token']
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            in_value = escape(form.cleaned_data['twitter_accounts'])
            if len(in_value) > 3000 or in_value.count('\n') > 55:
                return render(request, "index.html", {"form": form, "info": "Input too long"})
            request.session['form_value'] = in_value
        else:
            return render(request, "index.html", {"form": form, "info": "Form is not valid"})

    return redirect(authorization_url)


def do_report(request_token, oauth_verifier, accounts):
    logger = logging.getLogger(__name__)
    if not logger.hasHandlers():
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.INFO)

    output = ''
    try:
        twitter_auth = OAuthHandler(settings.CONSUMER_KEY, settings.CONSUMER_SECRET)
        twitter_auth.request_token = {'oauth_token': request_token, 'oauth_token_secret': oauth_verifier}
        twitter_auth.get_access_token(oauth_verifier)
        twitter_api = API(twitter_auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, retry_count=0, timeout=5)
        for account_name, account_type in accounts.items():
            output += 'Reporting: ' + account_name + '\n'
            try:
                if account_type == 'user_id':
                    user = twitter_api.report_spam(user_id=account_name, perform_block=False)
                else:
                    user = twitter_api.report_spam(screen_name=account_name, perform_block=False)
                output += 'Reported: https://twitter.com/' + user.screen_name + '\n'
                logger.info('Reported: https://twitter.com/' + user.screen_name)
            except TweepError as e:
                if e.api_code == 34:  # Account does not exist, skip
                    output += e.reason + '\n'
                else:
                    raise e
    except TweepError as e:
        output += e.reason + '\n'
    output += 'Done'
    return escape(output)
