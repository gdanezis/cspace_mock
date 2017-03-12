from json import loads, dumps
import requests

from hashlib import sha256
from binascii import hexlify

def H(x):
    return hexlify(sha256(x).digest())

class ChainSpace:
    def __init__(self):
        self.db = {} # Repository of objects
        self.active = {} # State of Active objects
        self.log = [] # A log of all transactions that were accepted
        self.head = "Ohm"

    def update_log(self, data):
        s = dumps(data)
        self.log.append(data)
        self.head = H(self.head + "|" + s)


    def apply_transaction(self, T):
        assert "contractMethod" in T
        assert "inputs" in T
        assert "referenceInputs" in T
        assert "parameters" in T
        assert "outputs" in T

        # Call the checker
        try:
            inputs_objs = [self.db[i] for i in T["inputs"]]
            ref_inputs_objs = [self.db[i] for i in T["referenceInputs"]]
        except KeyError as e:
            raise Exception("Object not in the Database: %s" % e.args[0])

        Check_T = {
            "contractMethod": T["contractMethod"],
            "inputs": inputs_objs,
            "referenceInputs": ref_inputs_objs,
            "parameters": T["parameters"],
            "outputs": T["outputs"]
        }

        # TODO: CALL THE CHECKER HERE

        # Derive fresh names:
        Tx_ID = H(dumps(T))
        Output_IDs = [H(Tx_ID+"|%s" % i) for i, _ in enumerate(T["outputs"])]

        # Now do the freshness checking
        for o in T["inputs"]:
            if self.active[o] != None:
                raise Exception("Object not Active: %s" % o)

        for o in T["referenceInputs"]:
            if self.active[o] != None:
                raise Exception("Object not Active: %s" % o)

        # Now make all objects non-fresh
        for o in T["inputs"]:
            self.active[o] = Tx_ID
            
        # Register new objects
        for idx, obj in zip(Output_IDs, T["outputs"]):
            self.db[idx] = dumps(obj)
            self.active[idx] = None

        # Setup as hashchain
        self.update_log((Tx_ID, T))

        return Tx_ID, Output_IDs
            

    def debug_register_object(self, O, ID=None):
        if ID is None:
            ID = H(O)
        assert ID not in self.db
        assert ID not in self.log

        self.db[ID] = O
        self.active[ID] = None

        return ID

# The webapp

from flask import Flask, request
app = Flask(__name__)

# Checker: http://192.168.0.15:4567

# The state of the infrastructure
app.cs = ChainSpace()

@app.route("/dump")
def dump():
    return dumps({"db": app.cs.db, "active": app.cs.active, "log":app.cs.log, "head":app.cs.head})

@app.route("/process")
def process():
    if request.method == "POST":
        T = loads(request.data)
        try:
            TxID, OutTx = app.cs.apply_transaction(T)
            return dumps({"status":"OK", "transactionId":TxID, "outputObjectIds":OutTx, "head":app.cs.head})
        except Exception as e:
            return dumps({"status":"Error", "message":e.args})
    else:
        return dumps({"status":"Error", "message":"Use POST method."})

@app.route("/debug_load")
def debugLoad():
    if request.method == "POST":
        T = loads(request.data)
        try:
            ID = app.cs.debug_register_object(T)
            return dumps({"status":"OK", "transactionId":ID, "head":app.cs.head})
        except Exception as e:
            return dumps({"status":"Error", "message":e.args})
    else:
        return dumps({"status":"Error", "message":"Use POST method."})



# Our mock ChainSpace service
if __name__ == "__main__":
    app.run()
