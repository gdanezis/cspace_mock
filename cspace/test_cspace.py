# The tests

import requests
from json import loads, dumps
from cspace.service import ChainSpace, app, request, process, dump, debugLoad
import pytest

Example_request = """{
        "contractMethod": "/bank/transfer",
        "inputs": [],
        "referenceInputs": [],
        "parameters": {},
        "outputs": []
}
"""

Sally_account = {"accountId": "Sally",
     "amount": 10
    }

Alice_account = {"accountId": "Alice",
     "amount": 0
    }

Bob_account = {"accountId": "Bob",
     "amount": 0
    }

Sally_account_new = {"accountId": "Sally",
     "amount": 2
    }

Alice_account_new = {"accountId": "Alice",
     "amount": 8
    }

Bob_account_new = {"accountId": "Bob",
     "amount": 5
    }


Example_transfer = {
        "contractMethod": "/bank/transfer",
        "inputs": [Sally_account, Alice_account],
        "referenceInputs": [],
        "parameters": {"amount":8},
        "outputs": [Sally_account_new, Alice_account_new]
}


def test_json():
    assert loads(Example_request)

def test_chainspace_register():
    cs = ChainSpace()
    O1 = dumps(Sally_account)
    O2 = dumps(Alice_account)
    cs.debug_register_object(O1)
    cs.debug_register_object(O2)

    with pytest.raises(AssertionError):
        cs.debug_register_object(O1)

def test_chainspace_Transaction():
    cs = ChainSpace()
    O1 = dumps(Sally_account)
    O2 = dumps(Alice_account)
    O3 = dumps(Bob_account)
    ID1 = cs.debug_register_object(O1)
    ID2 = cs.debug_register_object(O2)
    ID3 = cs.debug_register_object(O3)

    Example_transfer1 = {
        "contractMethod": "/bank/transfer",
        "inputs": [ID1, ID2],
        "referenceInputs": [],
        "parameters": {"amount":8},
        "outputs": [Sally_account_new, Alice_account_new]
    }

    Tx_ID, obj_IDs = cs.apply_transaction(Example_transfer1)

    Example_transfer2 = {
        "contractMethod": "/bank/transfer",
        "inputs": [ID1, ID3],
        "referenceInputs": [],
        "parameters": {"amount":5},
        "outputs": [Sally_account_new, Bob_account_new]
    }

    with pytest.raises(Exception):
        cs.apply_transaction(Example_transfer2)

    assert cs.log[0][0] == Tx_ID
    for oID in obj_IDs:
        assert oID in cs.active and cs.active[oID] is None
        assert oID in cs.db

## Define a test checker as a service

from flask import Flask, request
app = Flask(__name__)

"""

Example_transfer = {
        "contractMethod": "/bank/transfer",
        "inputs": [Sally_account, Alice_account],
        "referenceInputs": [],
        "parameters": {"amount":8},
        "outputs": [Sally_account_new, Alice_account_new]
}

"""

def start_app(app):
    app.run(threaded=True)

def ccheck(V, msg):
    if not V:
        raise Exception(msg)

@app.route("/bank/transfer", methods=["POST"])
def bank_transfer():
    if request.method == "POST":
        try:
            T = loads(request.data)
            T = T[u"transaction"]

            ccheck(T["contractMethod"] == "/bank/transfer", "Wrong Method")
            ccheck(len(T["referenceInputs"]) == 0, "Expect no references")

            from_account, to_account = T["inputs"]
            amount = T["parameters"]["amount"]
            from_account_new, to_account_new = T["outputs"] 

            ccheck(0 < amount, "Transfer should be positive")
            ccheck(from_account["accountId"] == from_account_new["accountId"], "Old and new account do not match")
            ccheck(to_account["accountId"] == to_account_new["accountId"], "Old and new account do not match")
            ccheck(amount <= from_account["amount"], "No funds available")
            ccheck(from_account["amount"] - amount == from_account_new["amount"], "Incorrect new balance")
            ccheck(to_account["amount"] + amount == to_account_new["amount"], "Incorrect new balance")
            

            return dumps({"status": True})
        except KeyError as e:
            return dumps({"status":False, "message":e.args})
        except Exception as e:
            return dumps({"status":False, "message":e.args})
    else:
        return dumps({"status":False, "message":"Use POST method."})


from threading import Thread

# @pytest.mark.skip(reason="Depends on Checker")
def test_request():
    t = Thread(target=start_app, args=(app,))
    t.start()

    try:
        T = dumps({"transaction": Example_transfer})
        r = requests.post(r"http://127.0.0.1:5000/bank/transfer", data = T)
        assert loads(r.text)["status"]
    except Exception as e:
        print "Error", e
    finally:
        t._Thread__stop()


def test_process():
    Sally_account = {"accountId": "Sally", "amount": 10 }
    Alice_account = {"accountId": "Alice", "amount": 0 }

    Sally_account_new = {"accountId": "Sally", "amount": 2 }
    Alice_account_new = {"accountId": "Alice", "amount": 8 }

    O1 = dumps(Sally_account)
    O2 = dumps(Alice_account)
    
    with app.test_request_context('/dump', method='POST', data=dumps(O1)):
        ID1 = loads(debugLoad())["transactionId"]

    with app.test_request_context('/dump', method='POST', data=dumps(O2)):
        ID2 = loads(debugLoad())["transactionId"]

    Example_transfer1 = {
        "contractMethod": "/bank/transfer",
        "inputs": [ID1, ID2],
        "referenceInputs": [],
        "parameters": {"amount":8},
        "outputs": [Sally_account_new, Alice_account_new]
    }

    with app.test_request_context('/process', method='POST', data=dumps(Example_transfer1)):
        # now you can do something with the request until the
        # end of the with block, such as basic assertions:
        assert request.path == '/process'
        assert request.method == 'POST'
        resp = loads(process())
        assert resp["status"] == "OK"

    with app.test_request_context('/dump', method='GET'):
        dump()

