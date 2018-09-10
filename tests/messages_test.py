# Execute with:
#   Repos/slack-notiphier/src $ ../venv/bin/python -m  pytest ../tests

import json
import os
from unittest.mock import patch

from slack_notiphier.webhook_firehose import WebhookFirehose
from slack_notiphier import config, logger

with patch.dict(os.environ, {'NOTIPHIER_CONFIG_FILE': '../tests/resources/slack-notiphier.cfg'}):
    config.reload()
    logger.reload()


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def _execute_test_from_file(test_filename, Phabricator, Slack, fixture_phab_users, fixture_slack_users):
    with open("../tests/resources/" + test_filename, 'r') as fp_test_spec:
        test_spec = json.load(fp_test_spec)

        # Mock Phabricator calls
        instance_phab = Phabricator.return_value
        instance_phab.user.search.return_value = fixture_phab_users
        instance_phab.transaction.search.side_effect = _mock_phab_call("transaction.search",
                                                                       test_spec["mocked_phab_calls"])
        instance_phab.differential.revision.search.side_effect = _mock_phab_call("differential.revision.search",
                                                                                 test_spec["mocked_phab_calls"])
        instance_phab.maniphest.search.side_effect = _mock_phab_call("maniphest.search",
                                                                     test_spec["mocked_phab_calls"])
        instance_phab.project.search.side_effect = _mock_phab_call("project.search",
                                                                   test_spec["mocked_phab_calls"])
        instance_phab.diffusion.repository.search.side_effect = _mock_phab_call("diffusion.repository.search",
                                                                                test_spec["mocked_phab_calls"])
        instance_phab.diffusion.querycommits.side_effect = _mock_phab_call("diffusion.querycommits",
                                                                           test_spec["mocked_phab_calls"])

        # Mock Slack calls
        instance_slack = Slack.return_value
        instance_slack.api_call.side_effect = _mock_slack_api_call(fixture_slack_users)

        webhook = WebhookFirehose()

        # Process the message from the file as if it came from Phabricator's Firehose. It then asserts Slack was
        # invoked with the right message.
        try:
            webhook.handle(test_spec["request"])

            for expected in test_spec["expected_responses"]:
                instance_slack.api_call.assert_any_call("chat.postMessage",
                                                        channel=expected['channel'],
                                                        attachments=expected['attachments'])
        except Exception as e:
            print("Exception in test. Some information about attempted Phab calls:", instance_phab.mock_calls)
            print("Exception in test. Some information about attempted Slack calls:", instance_slack.mock_calls)
            raise e


def _mock_phab_call(method, mocked_phab_calls):

    def inner_phab_call_handler(*args, **kwargs):
        if method not in mocked_phab_calls:
            raise ValueError("Mock Phabricator called with unexpected method: {} valid methods={}"
                             .format(method, mocked_phab_calls.keys()))

        for expected_call in mocked_phab_calls[method]:
            if expected_call["kwargs"] == kwargs:
                return expected_call["response"]

        raise ValueError("Mock Phabricator called with unexpected arguments: method={} args={} kwargs={}"
                         .format(method, args, kwargs))

    return inner_phab_call_handler


def _mock_slack_api_call(fixture_slack_users):

    def inner_slack_call_handler(method, *args, **kwargs):
        if method == "users.list":
            return fixture_slack_users

        if method == "chat.postMessage":
            return {'ok': True}

        raise ValueError("Invalid invocation to mocked slack_api_call: api_call({}, args={}, kwargs={})"
                         .format(method, args, kwargs))

    return inner_slack_call_handler


@patch("slackclient.SlackClient")
@patch("phabricator.Phabricator")
def test_welcome_message(Phabricator, Slack, fixture_phab_users, fixture_slack_users):
    """
        Simple test to ensure everything is correctly wired.
        Asserts we send the initial welcome message to Slack when the webhook starts running.
    """

    phab_instance = Phabricator.return_value
    phab_instance.user.search.return_value = fixture_phab_users

    slack_instance = Slack.return_value
    slack_instance.api_call.side_effect = _mock_slack_api_call(fixture_slack_users)

    WebhookFirehose()
    slack_instance.api_call.assert_called_with("chat.postMessage",
                                               channel="_slack_channel_",
                                               attachments=[{
                                                   'text': "Slack Notiphier started running.",
                                                   'color': '#28D7E5',
                                               }])


# Task Tests

def test_task_create(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-create.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_add_comment(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-add-comment.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_add_comment_with_mention(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-add-comment-with-mention.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_add_comment_own(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-add-comment-own.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_claim(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-claim.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_assign(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-assign.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_change_priority(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-change-priority.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_change_priority_own(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-change-priority-own.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_change_status(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-change-status.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_task_change_status_own(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("task-change-status-own.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


# Diff Revision Tests

def test_diff_create(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-create.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_update(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-update.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_abandon(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-abandon.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_reclaim(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-reclaim.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_accept(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-accept.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_request_changes(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-request-changes.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_commandeer(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-commandeer.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_add_comment(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-add-comment.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_add_comment_own(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-add-comment-own.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_add_comment_with_mention(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-add-comment-with-mention.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_create_notify_other_channel(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-create-notify-other-channel.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_add_comment_inline(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-add-comment-inline.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


def test_diff_add_comment_inline_own(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("diff-add-comment-inline-own.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


# Commit Tests

def test_commit_add_comment(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("commit-add-comment.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


# Project Tests

def test_proj_create(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("proj-create.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)


# Repository Tests

def test_repo_create(fixture_phab_users, fixture_slack_users):
    _execute_test_from_file("repo-create.json",
                            fixture_phab_users=fixture_phab_users,
                            fixture_slack_users=fixture_slack_users)
