##################################################################################
# Chainspace Mock
# test_bank_transfer.py
#
# version: 0.0.1
##################################################################################
import sys
sys.path.append('../../')
from json                   import loads, dumps
from threading              import Thread
from cspace_service         import app            as app_cspace
from sensor_data_checker    import app            as app_checker
import pytest
import requests


##################################################################################
# variables
##################################################################################
# checker URL
checker_url   =  r"http://127.0.0.1:5001/value/add"

# old accounts (before transaction)
sensor1_old = {"accountId": "sensor1", "temperature": [20, 21], "time" : ["T1", "T2"]}

# new accounts (after transaction)
sensor1_new = {"accountId": "sensor1", "temperature": [20, 21, 25], "time" : ["T1", "T2", "T3"]}

# example transfer 
Example_transfer = {
    "contractMethod"    : checker_url,
    "inputs"            : [sensor1_old],
    "referenceInputs"   : [],
    "parameters"        : {"temperature" : 25, "time" : "T3"},
    "outputs"           : [sensor1_new]
}
Example_invalid_transfer = {
    "contractMethod"    : checker_url,
    "inputs"            : [sensor1_old],
    "referenceInputs"   : [],
    "parameters"        : {"temperature" : 100, "time" : "T3"},
    "outputs"           : [sensor1_new]
}
Example_malformed_transfer = {
    "contractMethod"    : checker_url,
    # inputs are missing
    "referenceInputs"   : [],
    "parameters"        : {},
    "outputs"           : [sensor1_new]
}


##################################################################################
# run the checker's service
##################################################################################
def start_checker(app):
    try:
        app.run(host="127.0.0.1", port="5001", threaded=True)
    except Exception as e:
        print "\nThe checker is already running.\n"

def start_cspace(app): # pragma: no cover
    app.run(host="127.0.0.1", port="5000", threaded=True)



##################################################################################
# tests
##################################################################################
# -------------------------------------------------------------------------------
# test 1
# try to validate a transaction (call the checker) at an hardcoded address
# -------------------------------------------------------------------------------
def test_request():
    # run the checker
    t = Thread(target=start_checker, args=(app_checker,))
    t.start()

    try:
        # test a valid transfer
        r = requests.post(checker_url, data = dumps(Example_transfer))
        assert loads(r.text)["status"] == "OK"

        # test invalid transaction
        r = requests.post(checker_url, data = dumps(Example_invalid_transfer))
        assert loads(r.text)["status"] == "Error"

        # test malformed transaction
        r = requests.post(checker_url, data = dumps(Example_malformed_transfer))
        assert loads(r.text)["status"] == "Error"

        # try a get request
        r = requests.get(checker_url)
        assert loads(r.text)["status"] == "Error"

    finally:
        t._Thread__stop()


# -------------------------------------------------------------------------------
# test 2
# final check: test a complete transfer
# -------------------------------------------------------------------------------
def test_transaction():
    # run checker and cspace
    t1 = Thread(target=start_checker, args=(app_checker,))
    t1.start()
    t2 = Thread(target=start_cspace, args=(app_cspace,))
    t2.start()

    try:
        # add Alice's message to DB
        O1 = dumps(sensor1_old)
        r = requests.post(r"http://127.0.0.1:5000/debug_load", data = dumps(O1))
        assert loads(r.text)["status"] == "OK"
        ID1 = loads(r.text)["transactionId"]

        # define transfer
        T = {
            "contractMethod"  : checker_url,
            "inputs"          : [ID1],
            "referenceInputs" : [],
            "parameters"      : {"temperature" : 25, "time" : "T3"},
            "outputs"         : [sensor1_new]
        }

        # sumbit the transaction to the ledger
        r = requests.post(r"http://127.0.0.1:5000/process", data = dumps(T))
        assert loads(r.text)["status"] == "OK"

    finally:
        t1._Thread__stop()
        t2._Thread__stop()


##################################################################################