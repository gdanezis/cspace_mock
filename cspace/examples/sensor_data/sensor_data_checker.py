##################################################################################
# Chainspace Mock
# bank_transfer_checker.py
#
# version: 0.0.1
##################################################################################
from json  import loads, dumps
from flask import Flask, request


##################################################################################
# checker
##################################################################################   
# -------------------------------------------------------------------------------
# helper
# -------------------------------------------------------------------------------
def ccheck(V, msg):
    if not V:
        raise Exception(msg)

# -------------------------------------------------------------------------------
# checker
# -------------------------------------------------------------------------------  
def checker_function(T):
    # check transfer's format
    ccheck(T["contractMethod"]       == r"http://127.0.0.1:5001/value/add", "Wrong Method")
    ccheck(len(T["referenceInputs"]) == 0,                                  "Expect no references")
    ccheck(len(T["inputs"])          == 1,                                  "Expect only one input")
    ccheck(len(T["outputs"])         == 1,                                  "Expect only one output")

    # retrieve inputs 
    old         = T[u"inputs"][0]
    new         = T[u"outputs"][0]
    temperature = T[u"parameters"]["temperature"]
    time        = T[u"parameters"]["time"]

    # check old and new object id
    ccheck(old["accountId"] == new["accountId"],  "Old and new account do not match")

    # check that exactly one measurement has been added
    ccheck(len(old["temperature"]) == len(new["temperature"]) - 1,  "Only one measurement should be added")
    ccheck(len(old["time"])        == len(new["time"])        - 1,  "Only one measurement should be added")

    # check consistency of output objects
    ccheck((new["temperature"][-1] == temperature), "Output object not consisten with new temperature measurement")
    ccheck((new["time"][-1]       == time)        , "Output object not consisten with new timestamp")
    
    # return
    return {"status": "OK"}


##################################################################################
# webapp
##################################################################################
# the state of the infrastructure
app = Flask(__name__)

# -------------------------------------------------------------------------------
# /bank/transfer
# checker the correctness of a bank transfer
# -------------------------------------------------------------------------------
@app.route("/value/add", methods=["GET", "POST"])
def check():
    if request.method == "POST":
        try:
            return dumps(checker_function(loads(request.data)))
        except KeyError as e:
            return dumps({"status": "Error", "message": e.args})
        except Exception as e:
            return dumps({"status": "Error", "message": e.args})
    else:
        return dumps({"status": "Error", "message":"Use POST method."})


##################################################################################
# execute
##################################################################################
if __name__ == "__main__": 
    app.run(host="127.0.0.1", port="5001") 


##################################################################################