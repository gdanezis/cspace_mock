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
from cspace_service         import ChainSpace
from cspace_service         import app            as app_cspace
from hello_world_checker    import app            as app_checker
import pytest
import requests


##################################################################################
# variables
##################################################################################
# skeleton of chanspace request:
#
#   Example_request = """{
#       "contractMethod": "/URL/TO/CHECKER",
#       "inputs": [],
#       "referenceInputs": [],
#       "parameters": {},
#        "outputs": []
#   }
#   """

# checker URL
checker_url   =  r"http://127.0.0.1:5001"

# old accounts (before transaction)
Alice_message = {"accountId": "Alice", "message": ""}

# new accounts (after transaction)
Alice_message_new = {"accountId": "Alice", "message": "Hello, world!"}

# example transfer 
Example_transfer = {
    "contractMethod"    : checker_url,
    "inputs"            : [Alice_message],
    "referenceInputs"   : [],
    "parameters"        : {},
    "outputs"           : [Alice_message_new]
}
Example_invalid_transfer = {
    "contractMethod"    : checker_url,
    "inputs"            : [Alice_message],
    "referenceInputs"   : [],
    "parameters"        : {"some_param": "some_value"},
    "outputs"           : [Alice_message_new]
}
Example_malformed_transfer = {
    "contractMethod"    : checker_url,
    # inputs are missing
    "referenceInputs"   : [],
    "parameters"        : {},
    "outputs"           : [Alice_message_new]
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
#
# NOTE: since objects are unique, these tests can be run only once. To run the 
#       tests again, suppress the database files 'db.json', db_test2.json' and
#       'db_test4.json'.
##################################################################################
# -------------------------------------------------------------------------------
# test 1
# check json format
#
# NOTE: debug test, not needed to get 100% coverage
# -------------------------------------------------------------------------------
def test_json():
    assert loads(dumps(Example_transfer))


# -------------------------------------------------------------------------------
# test 2
# try add to Alice's message to the chainspace db
#
# NOTE: debug test, not needed to get 100% coverage
# -------------------------------------------------------------------------------
def test_chainspace_register():
    # # add object O1 and O2 to the DB
    O1 = dumps(Alice_message)
    cs = ChainSpace('db_test2.json')
    cs.debug_register_object(O1)
    # add O1 again: this should not work since objects are unique
    with pytest.raises(AssertionError):
        cs.debug_register_object(O1)


# -------------------------------------------------------------------------------
# test 3
# try to validate a transaction (call the checker) at an hardcoded address
# -------------------------------------------------------------------------------
def test_request():
    # run the checker
    t = Thread(target=start_checker, args=(app_checker,))
    t.start()

    try:
        # test a valid transfer
        r = requests.post(checker_url, data = dumps(Example_transfer))
        print r.text
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
# test 4
# try to execute a complete transaction
#
# NOTE: debug test, not needed to get 100% coverage
# -------------------------------------------------------------------------------
def test_process():
    # run the checker
    t = Thread(target=start_checker, args=(app_checker,))
    t.start()

    try:
        # save objects to DB
        cs = ChainSpace('db_test4.json')
        ID1 = cs.debug_register_object(dumps(Alice_message))

        # define a transaction
        T = {
            "contractMethod"  : checker_url,
            "inputs"          : [ID1],
            "referenceInputs" : [],
            "parameters"      : {},
            "outputs"         : [Alice_message_new]
        }
        
        # apply transaction
        cs.apply_transaction(T)

        # Re-execute the same transaction (objects are now not active)
        with pytest.raises(Exception):
            cs.apply_transaction(T)

    finally:
        t._Thread__stop()


# -------------------------------------------------------------------------------
# test 5
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
        O1 = dumps(Alice_message)
        r = requests.post(r"http://127.0.0.1:5000/debug_load", data = dumps(O1))
        assert loads(r.text)["status"] == "OK"
        ID1 = loads(r.text)["transactionId"]

        # define transfer
        T = {
            "contractMethod"  : checker_url,
            "inputs"          : [ID1],
            "referenceInputs" : [],
            "parameters"      : {},
            "outputs"         : [Alice_message_new]
        }

        # sumbit the transaction to the ledger
        r = requests.post(r"http://127.0.0.1:5000/process", data = dumps(T))
        print(r.text)
        assert loads(r.text)["status"] == "OK"

    finally:
        t1._Thread__stop()
        t2._Thread__stop()


##################################################################################