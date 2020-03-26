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
    csv_columns = ['MeetingName', 'Host', 'JoinUrl','InviteUrl']
    list_of_meetings_data = []

    # Open and read csv file
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
                attendees = row[4]
                agenda = row[5]
                
                attendees = attendees.replace(' ','')
                attendees = attendees.split(';')


                # Here we are swapping the date format from DD/MM/YYYY to MM/DD/YYYY 
                # Comment the two lines below if CSV file already has correct format

                start_time = list(start_time)
                start_time[0:2] ,start_time[3:5] = start_time[3:5],start_time[0:2]


                start_time = ''.join(start_time)
                start_time = start_time + ":00"

                try:
                    response = functions.CreateMeeting(functions.sessionSecurityContext,
                        meetingPassword = 'C!sco123',
                        meetingName = meeting_name,
                        agenda = agenda,
                        startDate = start_time,
                        duration = duration,
                        host = host,
                        attendees = attendees)

                    meeting_key = response.find('{*}body/{*}bodyContent/{*}meetingkey').text
                    print('Meeting Key:', meeting_key)

                except functions.SendRequestError as err:
                    print(err)
                    raise SystemExit

                try:
                    response = functions.GetMeetingUrl(functions.sessionSecurityContext,meeting_key)

                    meeting['JoinUrl'] = response.find('{*}body/{*}bodyContent/{*}joinMeetingURL').text
                    meeting['InviteUrl'] = response.find('{*}body/{*}bodyContent/{*}inviteMeetingURL').text
                    list_of_meetings_data.append(meeting)


                    print('Meeting url generated')

                    try:
                        with open('data.csv', 'w') as csvfile:
                            writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                            writer.writeheader()
                            for data in list_of_meetings_data:
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