##################################################################################
# Chainspace Mock
# cspace_service.py
#
# version: 0.0.1
##################################################################################
from json        import loads, dumps
from hashlib     import sha256
from binascii    import hexlify
from tinydb      import TinyDB, Query
import requests


##################################################################################
# wrap
# compute the hash of x
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
    # ----------------------------------------------------------------------------
    def __init__(self, dbName='db.json'):
        # init db
        db          = TinyDB(dbName)
        self.query  = Query()

        # repository of objects
        # contains objects of the form: {"id" : [ID], "object" : [Obj]}
        self.data   = db.table('data') 

        # state of Active objects
        # contains objects of the form: {"id" : [ID], "status" : [String]}
        self.active = db.table('active')    

        # a log of all transactions that were accepted
        # contains objects of the form: {"id" : [T_ID], "transaction" : [T_Obj]}
        self.log    = db.table('log')    

        # hash of transactions and output objects
        # contains ONE object of the form: {"head": [String]}
        self.head   = db.table('head')      

        # init hash of transactions and output objects
        self.head.insert({"head": "Ohm"})


    # ----------------------------------------------------------------------------
    # update_log
    # update the log with the input data.
    # ----------------------------------------------------------------------------
    def update_log(self, data):
        # append data to the log
        self.log.insert(data)

        # update head
        s = dumps(data)
        oldHead = self.head.all()
        newHead = H(dumps(oldHead[0]["head"]) + "|" + s)
        self.head.purge()
        self.head.insert({"head": newHead})


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
            for item in T["inputs"]:
                inputs_objs.append(loads(self.data.get(self.query.id == item)["object"]))
            for item in T["referenceInputs"]:
                ref_inputs_objs.append(loads(self.data.get(self.query.id == item)["object"]))
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
        for ID in T["inputs"]:
            o = self.active.get(self.query.id == ID)
            if o["status"] != None:
                raise Exception("Object not Active: %s" % ID)

        # verify that the reference input objects are active
        for ID in T["referenceInputs"]:
            o = self.active.get(self.query.id == ID)
            if o["status"] != None:
                raise Exception("Object not Active: %s" % ID)

        # now make all objects inactif    
        for ID in T["inputs"]:
            self.active.update({"status": Tx_ID}, self.query.id == ID)
            
        # register new objects
        for ID, obj in zip(Output_IDs, T["outputs"]):
            self.data.insert({"id" : ID, "object" : obj})
            self.active.insert({"id" : ID, "status" : None})

        # setup as hashchain: update the log
        self.update_log({"id" : Tx_ID, "transaction" : T})

        # return the transaction and object's output ID
        return Tx_ID, Output_IDs
        
        
    # ----------------------------------------------------------------------------
    # debug_register_object
    # debug method: create an object (add to DB) and returns its ID
    # ----------------------------------------------------------------------------
    def debug_register_object(self, O, ID=None):
        # check the format
        if ID is None:
            ID = H(dumps(O))
        assert self.data.search(self.query.id == ID) == []
        assert self.log.search(self.query.id == ID)  == []

        # create, save and set active the object
        self.data.insert({"id" : ID, "object" : O})
        self.active.insert({"id" : ID, "status" : None})

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
        "db"     : app.cs.data.all(), 
        "active" : app.cs.active.all(), 
        "log"    : app.cs.log.all(), 
        "head"   : app.cs.head.all()
    })

# -------------------------------------------------------------------------------
# /debug_load
# debug: store object in db and return the transaction's ID  
# -------------------------------------------------------------------------------
@app.route("/debug_load", methods=['GET', 'POST']) 
def debugLoad():
    if request.method == "POST":
        try:
            ID = app.cs.debug_register_object(loads(request.data) )
            return dumps({
                "status"        :"OK", 
                "transactionId" : ID
            })
        except Exception as e:
            return dumps({
                "status"  : "Error", 
                "message" : e.args
            })
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
                "head"            : app.cs.head.all()
            })
        except Exception as e:
            return dumps({
                "status"  : "Error", 
                "message" : e.args
            })
    else:
        return dumps({"status":"Error", "message":"Use POST method."})


##################################################################################
# execute
##################################################################################
if __name__ == "__main__":
    app.run(host="127.0.0.1", port="5000") 


##################################################################################