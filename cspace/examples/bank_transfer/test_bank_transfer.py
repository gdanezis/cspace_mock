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
from bank_transfer_checker  import app            as app_checker
import pytest
import requests


##################################################################################
# variables
##################################################################################
# checker URL
checker_url   =  r"http://127.0.0.1:5001/bank/transfer"

# old accounts (before money transfer)
Sally_account = {"accountId": "Sally", "amount": 10}
Alice_account = {"accountId": "Alice", "amount": 0}

# new accounts (after money transfer)
Sally_account_new = {"accountId": "Sally", "amount": 2}
Alice_account_new = {"accountId": "Alice", "amount": 8}

# example transfer 
Example_transfer = {
    "contractMethod"    : checker_url,
    "inputs"            : [Sally_account, Alice_account],
    "referenceInputs"   : [],
    "parameters"        : {"amount":8},
    "outputs"           : [Sally_account_new, Alice_account_new]
}
Example_invalid_transfer = {
    "contractMethod"    : checker_url,
    "inputs"            : [Sally_account, Alice_account],
    "referenceInputs"   : [],
    "parameters"        : {"amount":100},
    "outputs"           : [Sally_account_new, Alice_account_new]
}
Example_malformed_transfer = {
    "contractMethod"    : checker_url,
    # inputs are missing
    "referenceInputs"   : [],
    "parameters"        : {"amount":100},
    "outputs"           : [Sally_account_new, Alice_account_new]
}


##################################################################################
# run the checker's service
##################################################################################
def start_checker(app):
    try:
        app.run(host="127.0.0.1", port="5001", threaded=True)
    except Exception as e:
        print "The checker is already running."

def start_cspace(app):
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

        # test a transfer with invalid amount
        r = requests.post(checker_url, data = dumps(Example_invalid_transfer))
        assert loads(r.text)["status"] == "Error"

        # test malformed transaction
        r = requests.post(checker_url, data = dumps(Example_malformed_transfer))
        assert loads(r.text)["status"] == "Error"

        # get request
        r = requests.get(checker_url)
        assert loads(r.text)["status"] == "Error"

    finally:
        t._Thread__stop()


# -------------------------------------------------------------------------------
# test 2
# final check: simulate a complete transfer
# -------------------------------------------------------------------------------
def test_transaction():
    # run checker and cspace
    t1 = Thread(target=start_checker, args=(app_checker,))
    t1.start()
    t2 = Thread(target=start_cspace, args=(app_cspace,))
    t2.start()

    try:
        # add Alice's account to DB
        O1 = dumps(Sally_account)
        r = requests.post(r"http://127.0.0.1:5000/debug_load", data = dumps(O1))
        assert loads(r.text)["status"] == "OK"
        ID1 = loads(r.text)["transactionId"]

        # add Sally's account to DB
        O2 = dumps(Alice_account)
        r = requests.post(r"http://127.0.0.1:5000/debug_load", data = dumps(O2))
        assert loads(r.text)["status"] == "OK"
        ID2 = loads(r.text)["transactionId"]

        # define transfer
        T = {
            "contractMethod"  : "http://127.0.0.1:5001/bank/transfer",
            "inputs"          : [ID1, ID2],
            "referenceInputs" : [],
            "parameters"      : {"amount":8},
            "outputs"         : [Sally_account_new, Alice_account_new]
        }

        # sumbit the transaction to the ledger
        r = requests.post(r"http://127.0.0.1:5000/process", data = dumps(T))
        assert loads(r.text)["status"] == "OK"

    finally:
        t1._Thread__stop()
        t2._Thread__stop()


##################################################################################