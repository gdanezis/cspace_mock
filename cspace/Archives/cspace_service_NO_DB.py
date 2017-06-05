##################################################################################
# Chainspace Mock
# cspace_service.py
#
# version: 0.0.1
##################################################################################
from json       import loads, dumps
from hashlib    import sha256
from binascii   import hexlify
import requests


##################################################################################
# wraps
##################################################################################
def H(x):
    return hexlify(sha256(x).digest())


##################################################################################
# Chainspace's class
##################################################################################
class ChainSpace:
    # ----------------------------------------------------------------------------
    # init
    # At th moment, this function initialises all objects that will have be stored
    # in a database.
    #
    # TODO: store all obj in a database.
    # ----------------------------------------------------------------------------
    def __init__(self):
        self.db     = {}        # repository of objects
        self.active = {}        # state of Active objects
        self.log    = []        # a log of all transactions that were accepted
        self.head   = "Ohm"     # hash of transactions and output objects

    # ----------------------------------------------------------------------------
    # update_log
    # update the log with the input data.
    # ----------------------------------------------------------------------------
    def update_log(self, data):
        # append data to the log
        s = dumps(data)
        self.log.append(data)
        self.head = H(self.head + "|" + s)


    # ----------------------------------------------------------------------------
    # call checker
    # call the transaction's checker
    # ----------------------------------------------------------------------------
    def call_checker(self, packet):
        # call the checker
        r = requests.post(packet["contractMethod"], data = dumps(packet))
        # return result
        return loads(r.text)["status"] == "OK"

    # ----------------------------------------------------------------------------
    # apply_transaction
    # execute a transaction
    # ----------------------------------------------------------------------------
    def apply_transaction(self, T):
        # assert that the transaction is well-formed
        assert "contractMethod"  in T
        assert "inputs"          in T
        assert "referenceInputs" in T
        assert "parameters"      in T 
        assert "outputs"         in T

        # get inputs from the dabatase
        inputs_objs = []
        ref_inputs_objs = []
        try:
            for o in T["inputs"]:
                inputs_objs.append(loads(self.db[o]))
            for o in T["referenceInputs"]:
                ref_inputs_objs.append(loads(self.db[o]))
        except KeyError as e:
            raise Exception("Object not in the Database: %s" % e.args[0])

        # create a 'checked' transaction, with the inputs
        Check_T = {
            "contractMethod"  : T["contractMethod"],
            "inputs"          : inputs_objs,
            "referenceInputs" : ref_inputs_objs,
            "parameters"      : T["parameters"],  
            "outputs"         : T["outputs"]
        }
     
        # call the checker to verify integrity of the computation
        assert self.call_checker(Check_T)          

        # create fresh transaction IDs
        Tx_ID       = H(dumps(T))
        Output_IDs  = [H(Tx_ID+"|%s" % i) for i, _ in enumerate(T["outputs"])]

        # verify that the input objects are active
        for o in T["inputs"]:
            if self.active[o] != None:
                raise Exception("Object not Active: %s" % o)

        # verify that the reference input objects are active
        for o in T["referenceInputs"]:
            if self.active[o] != None:
                raise Exception("Object not Active: %s" % o)

        # now make all objects inactif    
        for o in T["inputs"]:
            self.active[o] = Tx_ID
            
        # register new objects
        for idx, obj in zip(Output_IDs, T["outputs"]):
            self.db[idx]     = dumps(obj)
            self.active[idx] = None

        # setup as hashchain: update the log
        self.update_log((Tx_ID, T))

        # return the transaction and object's output ID
        return Tx_ID, Output_IDs

    # ----------------------------------------------------------------------------
    # debug_register_object
    # debug method: create an object (add to DB) and returns its ID
    # ----------------------------------------------------------------------------
    def debug_register_object(self, O, ID=None):
        # check the format
        if ID is None:
            ID = H(O)
        assert ID not in self.db
        assert ID not in self.log

        # create, save and set active the object
        self.db[ID] = O
        self.active[ID] = None

        # return the ID
        return ID


##################################################################################
# webapp
##################################################################################
from flask import Flask, request

# the state of the infrastructure
app     = Flask(__name__)
app.cs  = ChainSpace()


# -------------------------------------------------------------------------------
# /
# test the server's connection
# -------------------------------------------------------------------------------
@app.route("/", methods=['GET', 'POST'])
def index():
    return dumps({"status": "OK", "message": "Hello, world!"})

# -------------------------------------------------------------------------------
# /dump
# serve the database content
# -------------------------------------------------------------------------------
@app.route("/dump", methods=['GET', 'POST'])
def dump():
    return dumps({
        "db"     : app.cs.db, 
        "active" : app.cs.active, 
        "log"    : app.cs.log, 
        "head"   : app.cs.head
    })

# -------------------------------------------------------------------------------
# /debug_load
# debug: return the transaction's ID  
# -------------------------------------------------------------------------------
@app.route("/debug_load", methods=['GET', 'POST']) 
def debugLoad():
    if request.method == "POST":
        try:
            ID = app.cs.debug_register_object(loads(request.data) )
            return dumps({"status":"OK", "transactionId":ID, "head":app.cs.head})
        except Exception as e:
            return dumps({"status":"Error", "message":e.args})
    else:
        return dumps({"status":"Error", "message":"Use POST method."}) 

# -------------------------------------------------------------------------------
# /process
# process a transaction 
# -------------------------------------------------------------------------------
@app.route("/process", methods=['GET', 'POST'])
def process():
    if request.method == "POST":
        try:
            TxID, OutTx = app.cs.apply_transaction(loads(request.data))
            return dumps({
                "status"          : "OK", 
                "transactionId"   : TxID, 
                "outputObjectIds" : OutTx, 
                "head"            : app.cs.head
            })
        except Exception as e:
            return dumps({"status":"Error", "message":e.args})
    else:
        return dumps({"status":"Error", "message":"Use POST method."})


##################################################################################
# execute
#
# Note:
# the server starts at 127.0.0.1 on port 5000
##################################################################################
if __name__ == "__main__":
    app.run(use_reloader=True)


##################################################################################