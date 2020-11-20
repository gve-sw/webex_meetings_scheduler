# Copyright (c) 2020 Cisco and/or its affiliates.
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import functions
import credentials
import csv
import datetime
import xml.etree.ElementTree as ET

if __name__ == "__main__":

    # AuthenticateUser and get sesssionTicket
    try:
        functions.sessionSecurityContext = functions.AuthenticateUser(
            credentials.sitename,
            credentials.username,
            credentials.password,
            credentials.access_token
        )

    # If an error occurs, print the error details and exit the script
    except functions.SendRequestError as err:
        print(err)
        raise SystemExit

    print("Authentication Accepted")
    print()
    print('Session Ticket:', '\n')
    print(functions.sessionSecurityContext['sessionTicket'])
    print()


    print('Now going to read csv file')
    input('Press Enter to continue...')

    # Header for the csv file that will generate the report
    csv_columns = ['MeetingKey', 'MeetingName', 'Host', 'JoinUrl','InviteUrl','sipURL', 'AlternateHosts']
    list_of_meetings_data = []

    # First  Open and read csv file to set delegate permissions by creating a list of all hosts
    # to schedule meetings for in the file and then iterating through them to add the admin account in
    # the delegate permissions
    list_of_hosts = []
    with open('meetings.csv','r') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = None

        for row_number, row in enumerate(csv_reader):
            if row_number is 0:
                header = row
                continue
            else:
                host = row[1]
                if host not in list_of_hosts:
                    list_of_hosts.append(host)

    for the_host in list_of_hosts:
        try:
            result=functions.SetDelegatePermissions(functions.sessionSecurityContext, the_host)
        except functions.SendRequestError as err:
            print(err)
            raise SystemExit


    # Now Open and read csv file to schedule meetings
    with open('meetings.csv','r') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = None

        for row_number, row in enumerate(csv_reader):

            if row_number is 0:
                header = row
                continue

            else:
                # making empty dictionary to add meeting info
                meeting = {}

                meeting_name = row[0]
                meeting['MeetingName'] = meeting_name

                host = row[1]
                meeting['Host'] = host

                start_time = row[2]
                duration = row[3]
                mtg_password = row[4]
                attendees = row[5]
                agenda = row[7]

                alternate_hosts = row[6]
                meeting['AlternateHosts'] = alternate_hosts
                alternate_hosts = alternate_hosts.replace(' ','')
                if alternate_hosts=='':
                    alternate_hosts=[]
                else:
                    alternate_hosts = alternate_hosts.split(';')
                print(alternate_hosts)

                attendees = attendees.replace(' ','')
                if attendees=='':
                    attendees=[]
                else:
                    attendees = attendees.split(';')
                #print(attendees)


                # Here we are swapping the date format from DD/MM/YYYY to MM/DD/YYYY 
                # Comment the two lines below if CSV file already has correct format

                #start_time = list(start_time)
                #start_time[0:2] ,start_time[3:5] = start_time[3:5],start_time[0:2]


                start_time = ''.join(start_time)
                start_time = start_time + ":00"

                # create 2 versions of the host to use to create the meeting because for some sites it errors out
                # when using the full email address and for others, when you just use the userid
                #first version is the full email address with domain
                hostfull=host
                #second version removes the domain and keeps just the username
                hostshort=host = host.split("@")[0]




                try:
                    response = functions.CreateMeeting(functions.sessionSecurityContext,
                        meetingPassword = mtg_password,
                        meetingName = meeting_name,
                        agenda = agenda,
                        startDate = start_time,
                        duration = duration,
                        host = hostfull,
                        attendees = attendees)

                    meeting_key = response.find('{*}body/{*}bodyContent/{*}meetingkey').text
                    print('Meeting Key:', meeting_key)


                    for alternate_host in alternate_hosts:
                        print('Setting alternate hosts...')
                        SetAlternateHost = functions.AlternateHost(functions.sessionSecurityContext,
                            meetingKey = meeting_key,
                            alternateHost = alternate_host)


                except functions.SendRequestError as err:
                    if err.reason!='The host WebExID does not exist':
                        #this is some other error that we are not anticipating, so just print and exit
                        print(err)
                        raise SystemExit
                    else:
                        try:
                            # since the error was specific to not liking the WebExID without host and we know with some sites
                            # that it is the case, now let's try it without removing the domain from host email
                            response = functions.CreateMeeting(functions.sessionSecurityContext,
                                                               meetingPassword='C!sco123',
                                                               meetingName=meeting_name,
                                                               agenda=agenda,
                                                               startDate=start_time,
                                                               duration=duration,
                                                               host=hostshort,
                                                               attendees=attendees)

                            meeting_key = response.find('{*}body/{*}bodyContent/{*}meetingkey').text
                            print('Meeting Key:', meeting_key)

                            for alternate_host in alternate_hosts:
                                print('Setting alternate hosts...')
                                SetAlternateHost = functions.AlternateHost(functions.sessionSecurityContext,
                                                                           meetingKey=meeting_key,
                                                                           alternateHost=alternate_host)

                        except functions.SendRequestError as err:
                            # this is still some other error that we are not anticipating, so just print and exit
                            print(err)
                            raise SystemExit

                try:
                    response = functions.GetMeetingUrl(functions.sessionSecurityContext,meeting_key)

                    meeting['JoinUrl'] = response.find('{*}body/{*}bodyContent/{*}joinMeetingURL').text
                    meeting['InviteUrl'] = response.find('{*}body/{*}bodyContent/{*}inviteMeetingURL').text
                    print('Meeting url generated')

                    

                    responseSIP = functions.GetMeeting(functions.sessionSecurityContext,meeting_key)
                    meeting['sipURL']= responseSIP.find('{*}body/{*}bodyContent/{*}sipURL').text
                    #result['serv:message']['serv:body'][0]['serv:bodyContent'][0]['meet:sipURL'][0]
                    print('Meeting SIP url generated')

                    list_of_meetings_data.append(meeting)
                    try:
                        with open('data.csv', 'w') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                            writer.writeheader()
                            for data in list_of_meetings_data:
                                meeting['MeetingKey'] = meeting_key
                                writer.writerow(data)
                    except IOError:
                        print("I/O error")



                except functions.SendRequestError as err:
                    print(err)
                    raise SystemExit


                print()
                print('Meeting Created for row ',row_number, '\n')
                print()

                input('Press Enter to continue...')
                continue