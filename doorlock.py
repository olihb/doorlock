import getopt
import pprint
import random
import re
import sys
import paho.mqtt.client as mqtt
import time
import sqlite3 as lite

# mqtt setup
mqtt_server = 'olihb.com'
mqtt_user = 'doorlock'
mqtt_password = ''
mqtt_topic = 'iot_messages'

# thresholds
data_timeout = 5*1000
data_nb_points = 10
msg_id = str(random.randint(1,1000))

database = "doorlock.db"

__author__ = 'olihb'

def get_data(device_id):

    data_collected = []
    current_milli_time = lambda: int(round(time.time() * 1000))
    mqtt_device_topic = mqtt_topic+'_command_'+device_id

    # callbacks
    def on_connect(client, userdata, flags, rc):
        client.subscribe(mqtt_topic)

    def on_message(client, userdata, msg):
        try:
            parse = re.search(r'type: ([^-\s]*) id: ([^-\s]*) value: ([^-\s]*)', msg.payload)
            if parse:
                type = parse.group(1)
                id = parse.group(2)
                value = parse.group(3)
                if (id == msg_id and type == 'raw'):
                    values = value.split(',')
                    userdata.append({'range': int(values[0]), 'rate': int(values[1])})
        except:
            print "parsing error: " + msg.payload


    # connect to mqtt server
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.user_data_set(data_collected)
    client.username_pw_set(mqtt_user, password=mqtt_password)
    client.connect(mqtt_server, 1883, 60)
    client.loop_start()

    start_time = current_milli_time()
    last_sent_message_time = current_milli_time()

    while (current_milli_time()<(start_time+data_timeout)):

        # wait 200ms before sending a new command
        if (current_milli_time()-last_sent_message_time)>200:
            client.publish(mqtt_device_topic,"get raw "+str(msg_id))
            last_sent_message_time = current_milli_time()

        if len(data_collected)>=data_nb_points:
            break

    client.loop_stop()
    client.disconnect()
    return data_collected


def initialize_db(cur):
    cur.execute("drop table if exists data_points")
    cur.execute("create table data_points (range int, rate int, tag int)")


def append_to_db(cur, data, tag):
    input = list()
    for point in data:
        input.append((point['range'], point['rate'], tag))
    cur.executemany("insert into data_points values (?,?,?)", input)

def predict(cur,):
    print ""

def main(argv):

    # setup variables
    device_id = ''
    tag = 0
    append = False
    init_db = False

    # parse arguments
    try:
        opts, args = getopt.getopt(argv, "d:a:p:i")
    except getopt.GetoptError:
        sys.exit(2)

    # iterate arguments
    for opt, arg in opts:

        # setup device
        if opt == '-d':
            device_id = arg

        # append new data to model
        if opt == '-a':
            append = True
            tag = int(arg)

        # add password
        if opt == '-p':
            global mqtt_password
            mqtt_password = arg

        # initialize database
        if opt == '-i':
            init_db = True

    # connect to db
    print "connect to database: %s" % (database)
    con = lite.connect(database)
    cur = con.cursor()

    # create new tables
    if init_db:
        print "initialize new tables (destructive)"
        initialize_db(cur)
        con.commit()

    # get data from sensor
    print "get data from sensor"
    data = get_data(device_id)
    print " data from sensor:"
    for point in data:
        print "\trange: %s\trate: %s" % (point['range'],point['rate'])

    # append to db
    if append:
        print "append data to db with tag: %s" % (tag)
        append_to_db(cur, data, tag)
        con.commit()

    # predict


if __name__ == "__main__":
    main(sys.argv[1:])