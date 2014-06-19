# -*- coding: utf-8 -*-
import http.client
import sublime
import sublime_plugin
import threading


DEFAULT_TEST_PATH = '/ppadmin/testrunner.py?m=text&scope='
DEAFULT_HTTP_METHOD = 'http://'


class UnittestCall(threading.Thread):
    def __init__(self, dev_env, test_run_path, view):
        """ The main threading part, runs class RunAllTestsCommand and RunSingleTestCommand
            in a thread not to freeze the editor
            @param dev_env: the base dev environment path
            @param test_run_path: the specific file to test, if any.
        """
        self.dev_env = dev_env
        self.test_path = test_run_path
        self.view = view

        self.result = None
        threading.Thread.__init__(self)

    def run(self):
        """
            Does the actual calling to your dev environment to run the tests.
            On error, it will alert you the error message
        """
        try:
            conn = http.client.HTTPConnection(self.dev_env)
            conn.request('GET', self.test_path)

            response = conn.getresponse()
            self.result = response.read()
            conn.close()
            resultStr = str(self.result, encoding='utf8' )
            self.status_msg = resultStr.split('\n')[-2:-1][0]
            return

        except Exception as e:
            print("Failed because of " + e)
            err = '%s: HTTP error contacting the server(are you on a bad vpn?)' % (__name__)

        sublime.error_message(err)
        self.result = False


class RunAllTestsCommand(sublime_plugin.TextCommand):

    def run(self, edit, save_event = False):

        self.load_settings()
        if save_event and not self.run_on_save:
            return 
        self.tests_to_run = self.get_test_file_path()
        self.threads = []
        self.call_tests()
        self.handle_threads()

    def load_settings(self):
        """ Loads all the settings from the .sublime-project file of the user.
        """
        settings = (
            self.view.window().active_view()
            .settings().get("projectplace_test_runner")
        )

        self.root_dev_env = 'pradeep'

        self.dev_env_domain = settings.get(
            'domain', self.view.window().folders()[0]
        )
        self.run_on_save = settings.get(
            'run_on_save', False
        )
        
        self.dev_env = self.root_dev_env + self.dev_env_domain
        self.http_method = DEAFULT_HTTP_METHOD
        self.test_root = self.http_method + self.dev_env + DEFAULT_TEST_PATH

    def get_test_file_path(self):
        """ Returns nothing since we want to run all test file that we have.
        """
        return ''

    def call_tests(self):
        """ Calls the test cgi on the specific development environment and then prints the result.
        """
        test_run_path = self.test_root + self.tests_to_run
        thread = UnittestCall(self.dev_env, test_run_path, self.view)
        self.threads.append(thread)
        thread.start()

    def handle_threads(self, loops=0, dots='.'):
        """
            Loops and checks the thread(s) if any of them are currently working(then wait), if the
            call to the tests have failed(pass it) or if the thread is done, prints the result to the
            Sublime console.
        """
        next_threads = []
        for thread in self.threads:
            if thread.is_alive():
                next_threads.append(thread)
                continue
            if thread.result is False:
                continue

            resultStr = str(thread.result, encoding='utf8')
            print (resultStr)
            self.view.set_status('pp-unitest-result', 'Projectplace - ' + thread.status_msg)
            sublime.set_timeout(lambda: self.view.erase_status('pp-unitest-result'), 5000)
            
        threads = next_threads

        if len(threads):
            if loops < 8:
                dots += '.'
                loops += 1
            else:
                dots = '.'
                loops = 0
            self.view.set_status('pp-unitest-call', 'Projectplace - In Tests We Trust%s' % (dots))
            sublime.set_timeout(lambda: self.handle_threads(loops, dots), 200)
            return

        self.view.erase_status('pp-unitest-call')


class RunSingleTestCommand(RunAllTestsCommand):

    def get_test_file_path(self):
        """ Returns the path to the test file that we want to test.
            @param self: The single test command instance
        """
        import os
        DEFAULT_TEST_ROOT = 'tests'
        current_file = self.view.file_name().split(self.root_dev_env)[1]

        if current_file.find(DEFAULT_TEST_ROOT) is -1:
            return DEFAULT_TEST_ROOT + current_file
        else:
            return current_file.lstrip(os.sep)

class RunSingleTestCommandOnSave(sublime_plugin.EventListener):
    def on_post_save(self, view):
        single_run = RunSingleTestCommand(view)
        single_run.run(view, True)
        
