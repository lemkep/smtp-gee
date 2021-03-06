#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
This lives in https://github.com/treibholz/smtp-gee
'''

import smtplib
import configparser
import time
import hashlib
import socket
import imaplib
import argparse
import sys

from email.mime.text import MIMEText

socket.setdefaulttimeout(10)


class Account(object): # {{{
    """docstring for Account"""
    def __init__(self, name, login=False, password=False, smtp_server="localhost", imap_server="localhost", smtp_over_ssl=False, smtp_port=25): # {{{
        super(Account, self).__init__()
        self.name           =   name
        self.login          =   login
        self.password       =   password
        self.smtp_server    =   smtp_server
        self.smtp_port      =   smtp_port
        self.imap_server    =   imap_server
        self.email          =   login
        self.smtp_timeout   =   30
        self.imap_timeout   =   30

        self.__debug        =   False
        self.smtp_over_ssl  =   smtp_over_ssl
        self.error_string   =   ""

    # }}}

    def send(self, recipient): # {{{
        """docstring for send"""

        timestamp = time.time()

        payload = """Hi,
this is a testmail, generated by SMTP-GEE.

sent on:   %s
sent at:   %s
sent from: %s
sent to:   %s

Cheers.
    SMTP-GEE

""" % (socket.getfqdn(), timestamp, self.email, recipient.email, )


        test_id = hashlib.sha1(payload.encode('utf-8')).hexdigest()


        msg = MIMEText(payload)

        msg['From']     =   self.email
        msg['To']       =   recipient.email
        msg['Subject']  =   "[SMTP-GEE] |%s" % (test_id, )

        try:
            if self.smtp_over_ssl:
                if self.__debug: print("SMTP-over-SSL is used")
                s = smtplib.SMTP_SSL( self.smtp_server, port = self.smtp_port, timeout = self.smtp_timeout)
            else:
                if self.__debug: print("SMTP is used")
                s = smtplib.SMTP( self.smtp_server, port = self.smtp_port, timeout = self.smtp_timeout)
                s.starttls()

            #s.set_debuglevel(2)
            s.login(self.login, self.password )

            s.sendmail( self.email, recipient.email, msg.as_string() )
            s.quit()

            return test_id
        except smtplib.SMTPAuthenticationError as smtp_error:
            self.error_string += "SMTPAuthenticationError: {0}".format(smtp_error)
            return False
        except smtplib.SMTPConnectError as smtp_error:
            self.error_string += "SMTPConnectError: {0}".format(smtp_error)
            return False
        except:
            self.error_string += "Unexpected error: {0}".format(sys.exc_info())
            return False


    # }}}

    def check(self, check_id, stopwatch=None): # {{{
        """docstring for check"""

        try:
            m = imaplib.IMAP4_SSL(self.imap_server)

            m.login(self.login, self.password)
            m.select()

            data=[b'']

            count = 0
            # Wait until the message is there.
            while data == [b'']:
                if stopwatch != None:
                    if stopwatch.gettime() > self.imap_timeout:
                        return False
                typ, data = m.search(None, 'SUBJECT', '"%s"' % check_id)
                time.sleep(1)
                count += 1

            for num in data[0].split():
                typ, _data = m.fetch(num, '(RFC822)')
                msg = _data[0][1]

            # deleting should be more sophisticated, for debugging...
            m.store(num, '+FLAGS', r'\Deleted')
            m.expunge()
            m.close()
            m.logout()

            return True
        except imaplib.IMAP4.error as imap_error:
            self.error_string += "IMAP error: {0}".format(imap_error) 
            return False
        except:
            self.error_string += "Unexpected error: {0}".format(sys.exc_info())
            return False
    # }}}

    def set_debug(self, debug): # {{{
        """docstring for set_debug"""
        self.__debug = debug

    # }}}

# }}}

class Stopwatch(object): # {{{
    """docstring for Stopwatch"""
    def __init__(self, debug=False):
        super(Stopwatch, self).__init__()
        self.__debug = debug
        self.__start   = -1
        self.counter = 0

    def gettime(self):
        return time.time() - self.__start

    def start(self):
        """docstring for start"""
        self.__start = time.time()

    def stop(self):
        """docstring for stop"""
        self.counter += time.time() - self.__start
        self.__start  = -1

# }}}

if __name__ == "__main__":

    # fallback returncode
    returncode = 3

    # Parse Options # {{{
    parser = argparse.ArgumentParser(
        description='Check how long it takes to send a mail (by SMTP) and how long it takes to find it in the IMAP-inbox',
        epilog = "Because e-mail is a realtime-medium and you know it!")


    main_parser_group = parser.add_argument_group('Main options')
    main_parser_group.add_argument('--from', dest='sender', action='store',
                    required=True,
                    metavar="<name>",
                    help='The account to send the message')

    main_parser_group.add_argument('--rcpt', dest='rcpt', action='store',
                    required=True,
                    metavar="<name>",
                    help='The account to receive the message')

    main_parser_group.add_argument('--nagios', dest='nagios', action='store_true',
                    required=False,
                    default=False,
                    help='output in Nagios mode')

    main_parser_group.add_argument('--except-means', dest='except_return', action='store',
                    metavar="<int>",
                    required=False,
                    default=2,
                    help='Map Exceptions to another returncode. Default: %(default)s')

    main_parser_group.add_argument('--debug', dest='debug', action='store_true',
                    required=False,
                    default=False,
                    help='Debug mode')

    main_parser_group.add_argument('--config',dest='config_file', action='store',
                    default='config.ini',
                    metavar="<file>",
                    required=False,
                    help='alternate config-file')


    smtp_parser_group = parser.add_argument_group('SMTP options')
    smtp_parser_group.add_argument('--smtp_warn', dest='smtp_warn', action='store',
                    required=False,
                    default=15,
                    metavar="<sec>",
                    type=int,
                    help='warning threshold to send the mail. Default: %(default)s')

    smtp_parser_group.add_argument('--smtp_crit', dest='smtp_crit', action='store',
                    required=False,
                    default=30,
                    metavar="<sec>",
                    type=int,
                    help='critical threshold to send the mail. Default: %(default)s')

    smtp_parser_group.add_argument('--smtp_timeout', dest='smtp_timeout', action='store',
                    required=False,
                    default=30,
                    metavar="<sec>",
                    type=int,
                    help='timeout to stop sending a mail. Default: %(default)s')


    imap_parser_group = parser.add_argument_group('IMAP options')
    imap_parser_group.add_argument('--imap_warn', dest='imap_warn', action='store',
                    required=False,
                    default=20,
                    metavar="<sec>",
                    type=int,
                    help='warning threshold until the mail appears in the INBOX. Default: %(default)s')

    imap_parser_group.add_argument('--imap_crit', dest='imap_crit', action='store',
                    required=False,
                    default=30,
                    metavar="<sec>",
                    type=int,
                    help='critical threshold until the mail appears in the INBOX. Default: %(default)s')

    imap_parser_group.add_argument('--imap_timeout', dest='imap_timeout', action='store',
                    required=False,
                    default=30,
                    metavar="<sec>",
                    type=int,
                    help='timeout to stop waiting for a mail to appear in the INBOX (not implemented yet). Default: %(default)s')


    args = parser.parse_args()

    # }}}

    # Read Config {{{

    c = configparser.ConfigParser()
    c.read(args.config_file)

    a={}

    for s in c.sections():
        a[s] = Account(s)

        a[s].set_debug(args.debug)

        # This has to be more easy...
        a[s].smtp_server    = c.get(s, 'smtp_server')
        a[s].imap_server    = c.get(s, 'imap_server')
        a[s].password       = c.get(s, 'password')
        a[s].login          = c.get(s, 'login')
        a[s].email          = c.get(s, 'email')
        a[s].smtp_timeout   = args.smtp_timeout
        a[s].imap_timeout   = args.imap_timeout

        # FIXME: Really, really Ugly!
        a[s].smtp_port = 25
        try:
            a[s].smtp_over_ssl = c.get(s, 'smtp_over_ssl')
            a[s].smtp_port = 465
        except:
            pass

        try:
            a[s].smtp_port = c.get(s, 'smtp_port')
        except:
            pass


    # }}}

    ### Here the real work begins  ###

    # Create the stopwatches.
    smtp_time = Stopwatch()
    imap_time = Stopwatch()

    # send the mail by SMTP
    smtp_time.start()
    smtp_result = a[args.sender].send(a[args.rcpt])
    smtp_time.stop()

    if args.debug:
        print(smtp_result)

    if smtp_result:

        # Receive the mail.
        imap_time.start()
        imap_result = a[args.rcpt].check(smtp_result, stopwatch=imap_time)
        imap_time.stop()


    ### Present the results

    if not args.nagios:

        # Default output
        print("SMTP, (%s) time to send the mail: %.3f sec." % (args.sender, smtp_time.counter, ))
        print("IMAP, (%s) time until the mail appeared in the destination INBOX: %.3f sec." % (args.rcpt, imap_time.counter, ))

    else:

        # Nagios output
        # this could be beautified...

        nagios_code = ('OK', 'WARNING', 'CRITICAL', 'UNKNOWN' )

        if   ((smtp_time.counter >= args.smtp_crit) or (imap_time.counter >= args.imap_crit)):
            returncode = 2
        elif ((smtp_time.counter >= args.smtp_warn) or (imap_time.counter >= args.imap_warn)):
            returncode = 1
        else:
            returncode = 0

        if not smtp_result: # if it failed
            returncode = int(args.except_return)
            error_string = a[args.sender].error_string
            nagios_template="%s: (%s->%s) SMTP failed in %.3f sec, NOT received in %.3f sec (%s)|smtp=%.3f;%.3f;%.3f imap=%.3f;%.3f;%.3f"
        elif not imap_result: # if it failed
            error_string = a[args.rcpt].error_string
            returncode = int(args.except_return)
            nagios_template="%s: (%s->%s) sent in %.3f sec, IMAP failed, NOT received in %.3f sec (%s)|smtp=%.3f;%.3f;%.3f imap=%.3f;%.3f;%.3f"
        else:
            error_string=""
            nagios_template="%s: (%s->%s) sent in %.3f sec, received in %.3f sec%s|smtp=%.3f;%.3f;%.3f imap=%.3f;%.3f;%.3f"

        print(nagios_template % (
            nagios_code[returncode],
            args.sender,
            args.rcpt,
            smtp_time.counter,
            imap_time.counter,
            error_string,
            smtp_time.counter,
            args.smtp_warn,
            args.smtp_crit,
            imap_time.counter,
            args.imap_warn,
            args.imap_crit,
        ))

        sys.exit(returncode)

## vim:fdm=marker:ts=4:sw=4:sts=4:ai:sta:et
