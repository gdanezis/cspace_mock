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

@pytest.mark.skip(reason="Depends on Checker")
def test_request():
    T = dumps(Example_transfer)
    r = requests.post(r"http://192.168.0.15:4567/bank/transfer", data = {"transaction": T})
    print loads(r.text)


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

