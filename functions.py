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

import requests
import datetime
from lxml import etree
import credentials
import xml.etree.ElementTree as ET

# Change to true to enable request/response debug output
DEBUG = False

# Once the user is authenticated, the sessionTicket for all API requests will be stored here
sessionSecurityContext = {}


# Custom exception for errors when sending requests
class SendRequestError(Exception):

    def __init__(self, result, reason):
        self.result = result
        self.reason = reason

    pass


# Generic function for sending XML API requests
#   envelope : the full XML content of the request
def sendRequest(envelope):
    if DEBUG:
        print(envelope)

    # Use the requests library to POST the XML envelope to the Webex API endpoint
    headers = {'Content-Type': 'application/xml'}
    response = requests.post('https://api.webex.com/WBXService/XMLService', envelope)

    # Check for HTTP errors
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        raise SendRequestError('HTTP ' + str(response.status_code), response.content.decode("utf-8"))

    # Use the lxml ElementTree object to parse the response XML
    message = etree.fromstring(response.content)

    if DEBUG:
        print(etree.tostring(message, pretty_print=True, encoding='unicode'))

        # Use the find() method with an XPath to get the 'result' element's text
    # Note: {*} is pre-pended to each element name - ignores namespaces
    # If not SUCCESS...
    if message.find('{*}header/{*}response/{*}result').text != 'SUCCESS':
        result = message.find('{*}header/{*}response/{*}result').text
        reason = message.find('{*}header/{*}response/{*}reason').text

        # ...raise an exception containing the result and reason element content
        raise SendRequestError(result, reason)

    return message


def AuthenticateUser(siteName, webExId, password, accessToken):
    # If an access token is provided in .env, we'll use this form
    if (accessToken):
        request = f'''<?xml version="1.0" encoding="UTF-8"?>
            <serv:message xmlns:serv="http://www.webex.com/schemas/2002/06/service"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <header>
                    <securityContext>
                        <siteName>{siteName}</siteName>
                        <webExID>{webExId}</webExID>
                    </securityContext>
                </header>
                <body>
                    <bodyContent xsi:type="java:com.webex.service.binding.user.AuthenticateUser">
                        <accessToken>{accessToken}</accessToken>
                    </bodyContent>
                </body>
            </serv:message>'''
    else:
        # If no access token, assume a password was provided, using this form
        request = f'''<?xml version="1.0" encoding="UTF-8"?>
            <serv:message xmlns:serv="http://www.webex.com/schemas/2002/06/service"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                <header>
                    <securityContext>
                        <siteName>{siteName}</siteName>
                        <webExID>{webExId}</webExID>
                        <password>{password}</password>
                    </securityContext>
                </header>
                <body>
                    <bodyContent xsi:type="java:com.webex.service.binding.user.AuthenticateUser"/>
                </body>
            </serv:message>'''

    # Make the API request
    response = sendRequest(request)

    # Return an object containing the security context info with sessionTicket
    return {
        'siteName': siteName,
        'webExId': webExId,
        'sessionTicket': response.find('{*}body/{*}bodyContent/{*}sessionTicket').text
    }

def SetDelegatePermissions(sessionSecurityContext, host):
    request = f'''<?xml version="1.0" encoding="UTF-8"?>
                <serv:message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:serv="http://www.webex.com/schemas/2002/06/service">
                  <header>
                    <securityContext>
                    <siteName>{sessionSecurityContext["siteName"]}</siteName>
                    <webExID>{sessionSecurityContext["webExId"]}</webExID>
                    <sessionTicket>{sessionSecurityContext["sessionTicket"]}</sessionTicket>  
                    </securityContext>
                  </header>
                  <body>
                    <bodyContent xsi:type="java:com.webex.service.binding.user.SetUser">
                      <webExId>{host}</webExId>
                      <schedulingPermission>{sessionSecurityContext["webExId"]}</schedulingPermission>
                    </bodyContent>
                  </body>
                </serv:message>'''
    response = sendRequest(request)
    return response

def CreateMeetingBuildRequest(sessionSecurityContext, meetingPassword, meetingName, agenda, startDate, duration, host,
                              attendees):
    request = f'''<?xml version="1.0" encoding="UTF-8"?>
        <serv:message xmlns:serv="http://www.webex.com/schemas/2002/06/service"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <header>
                <securityContext>
                    <siteName>{sessionSecurityContext["siteName"]}</siteName>
                    <webExID>{sessionSecurityContext["webExId"]}</webExID>
                    <sessionTicket>{sessionSecurityContext["sessionTicket"]}</sessionTicket>  
                </securityContext>
            </header>
            <body>
                <bodyContent
                    xsi:type="java:com.webex.service.binding.meeting.CreateMeeting">
                    <accessControl>
                        <meetingPassword>{meetingPassword}</meetingPassword>
                    </accessControl>
                    <metaData>
                        <confName>{meetingName}</confName>
                        <agenda>{agenda}</agenda>
                    </metaData>
                    <participants>
                        <attendees>
                        </attendees>
                    </participants>
                    <enableOptions>
                        <chat>true</chat>
                        <poll>true</poll>
                        <audioVideo>true</audioVideo>
                        <supportE2E>TRUE</supportE2E>
                        <autoRecord>TRUE</autoRecord>
                    </enableOptions>
                    <schedule>
                        <startDate>{startDate}</startDate>
                        <openTime>900</openTime>
                        <joinTeleconfBeforeHost>false</joinTeleconfBeforeHost>
                        <duration>{duration}</duration>
                        <hostWebExID>{host}</hostWebExID>
                    </schedule>
                    <telephony>
                        <telephonySupport>CALLIN</telephonySupport>
                        <extTelephonyDescription>
                            Call 1-800-555-1234, Passcode 98765
                        </extTelephonyDescription>
                    </telephony>
                    <remind>
            	        <enableReminder>True</enableReminder>
            	        <sendEmail>True</sendEmail>
                    </remind>
                    <attendeeOptions>
            	        <emailInvitations>True</emailInvitations>
                    </attendeeOptions>
                </bodyContent>
            </body>
        </serv:message>'''

    # here we are reading the request xml string and appending the attendees by emails

    tree = ET.ElementTree(ET.fromstring(request))

    for address in attendees:
        root = tree.getroot()
        body = root[1][0][2][0]

        tree = ET.ElementTree(ET.fromstring(request))
        root = tree.getroot()
        body = root[1][0][2][0]
        attendee = ET.SubElement(body, "attendee")
        person = ET.SubElement(attendee, "person")
        name = ET.SubElement(person, "name")
        email = ET.SubElement(person, "email")

        name.text = address
        email.text = address
        request = ET.tostring(root)

    return request


def CreateMeeting(sessionSecurityContext, meetingPassword, meetingName, agenda, startDate, duration, host, attendees):
    request = CreateMeetingBuildRequest(sessionSecurityContext, meetingPassword, meetingName, agenda, startDate,
                                        duration, host, attendees)

    response = sendRequest(request)

    return response


def GetMeetingUrl(sessionSecurityContext, meetingKey):
    request = f'''<?xml version="1.0" encoding="UTF-8"?>
        <serv:message xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <header>
                <securityContext>
                    <siteName>{sessionSecurityContext["siteName"]}</siteName>
                    <webExID>{sessionSecurityContext["webExId"]}</webExID>
                    <sessionTicket>{sessionSecurityContext["sessionTicket"]}</sessionTicket>  
                </securityContext>
            </header>
            <body>
                <bodyContent
                    xsi:type="java:com.webex.service.binding.meeting.GetjoinurlMeeting">
                    <sessionKey>{meetingKey}</sessionKey>
                </bodyContent>
            </body>
        </serv:message>'''

    response = sendRequest(request)

    return response


def GetMeeting(sessionSecurityContext, meetingKey):
    request = f'''<?xml version="1.0" encoding="ISO-8859-1"?>
                <serv:message
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xmlns:serv="http://www.webex.com/schemas/2002/06/service">
                    <header>
                        <securityContext>
                            <siteName>{sessionSecurityContext["siteName"]}</siteName>
                            <webExID>{sessionSecurityContext["webExId"]}</webExID>
                            <sessionTicket>{sessionSecurityContext["sessionTicket"]}</sessionTicket>
                        </securityContext>
                    </header>
                    <body>
                        <bodyContent xsi:type="java:com.webex.service.binding.meeting.GetMeeting">
                            <meetingKey>{meetingKey}</meetingKey>
                        </bodyContent>
                    </body>
                </serv:message>'''

    response = sendRequest(request)

    return response


def AlternateHost(sessionSecurityContext, meetingKey, alternateHost):
    request = f''' <?xml version="1.0" encoding="UTF-8"?>
                    <serv:message xmlns:serv="http://www.webex.com/schemas/2002/06/service"
                        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
                        <header>
                            <securityContext>
                                <siteName>{sessionSecurityContext["siteName"]}</siteName>
                                <webExID>{sessionSecurityContext["webExId"]}</webExID>
                                <sessionTicket>{sessionSecurityContext["sessionTicket"]}</sessionTicket>  
                            </securityContext>
                        </header>
                        <body>
                            <bodyContent xsi:type="java:com.webex.service.binding.attendee.CreateMeetingAttendee">
                                <person>
                                    <name>{alternateHost}</name>
                                    <address>
                                        <addressType>PERSONAL</addressType>
                                    </address>
                                    <email>{alternateHost}</email>
                                    <type>VISITOR</type>
                                </person>
                                <role>HOST</role>
                                <sessionKey>{meetingKey}</sessionKey>
                            </bodyContent>
                        </body>
                    </serv:message>'''
    response = sendRequest(request)
    return response
