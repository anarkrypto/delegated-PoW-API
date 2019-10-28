from flask import Flask, jsonify, request
from functions import block_create, balance, frontier, broadcast, get_difficulty, solve_work, get_my_ip, pending_filter, receive, check_history, register, encode_ip, worker, register_config
from nanolib import Block, validate_account_id, validate_private_key, get_account_id
import requests
import json
import waitress

app = Flask(__name__)

#Check config
try:
    validate_account_id(worker["account"])
    validate_private_key(worker["private_key"])
    validate_account_id(worker["representative"])
except Exception as e:
    print ("Invalid worker_config.json settings found! Details: ")
    print (e)
    quit()

#Check if key pair is valid
if worker["account"] != get_account_id(private_key=worker["private_key"], prefix="nano_"):
    print ("Invalid key pair")
    quit()
print ("Configurations okay")

#Check if Node is online
try:
    r = requests.post(worker["node"], json={"action": "version"})
except:
    print ("Node " + worker["node"] + " Offline! Exiting")
    quit()
else:
    if "node_vendor" in r.json():
        print ("Node (" + r.json()["node_vendor"] + ") is online on " + worker["node"])
    else:
        print ("Node " + worker["node"] + " error! Exiting")
        quit()

#Registration Process
print ("Checking register")
history = check_history(worker["account"], register_config["account"])
if history is not None:
    if int(history["amount"]) == register_config["sign_new_account_code"]:
        print ("Found your worker account registration: " + worker["account"])
        myIP = get_my_ip() #check IP register
        ip_account = encode_ip(myIP)
        history = check_history(worker["account"], ip_account)
        if history is not None:
            print ("Found your actuall IP address registration: " + myIP)
            if int(history["amount"]) != register_config["sign_new_ip_code"]:
                print ("Incorrect amount in your IP address register")
                try_r = register (worker["account"], worker["representative"], frontier(worker["account"]), ip_account, register_config["sign_new_ip_code"], 1.0)
                if (try_r is False):
                    quit()
        else:
            print ("Not found your actuall IP address registration: " + myIP)
            try_r  = register (worker["account"], worker["representative"], frontier(worker["account"]), ip_account, register_config["sign_new_ip_code"], 1.0)
            if (try_r is False):
                quit()
    else:
        print ("Incorrect amount in register")
        try_r = register (worker["account"], worker["representative"], frontier(worker["account"]), register_config["account"], register_config["sign_new_account_code"], 1.0)
        if (try_r is False):
            quit()
else:
    print ("Not found your worker registration: " + worker["account"])
    try_r = register (worker["account"], worker["representative"], frontier(worker["account"]), register_config["account"], register_config["sign_new_account_code"], 1.0)
    if (try_r is False):
        quit()
    else:
        myIP = get_my_ip() #check IP register
        ip_account = encode_ip(myIP)
        history = check_history(worker["account"], ip_account)
        if history is not None:
            print ("Found your actuall IP address registration: " + myIP)
            if int(history["amount"]) != register_config["sign_new_ip_code"]:
                print ("Incorrect amount in your IP address register")
                try_r = register (worker["account"], worker["representative"], frontier(worker["account"]), ip_account, register_config["sign_new_ip_code"], 1.0)
                if (try_r is False):
                    quit()
        else:
            print ("Not found your actuall IP address registration: " + myIP)
            try_r = register (worker["account"], worker["representative"], frontier(worker["account"]), ip_account, register_config["sign_new_ip_code"], 1.0)
            if (try_r is False):
                quit()

#convert mNano fee to raws
worker["fee"] = int(worker["fee"] * 1000000000000000000000000000000)

#Listen /open_request
@app.route('/open_request', methods=['GET', 'POST'])
def opening_request():
    print ("Open Request")
    header = {"version": "0.0.1", "reward_account": worker["account"], "fee": worker["fee"], "max_multiplier": worker["max_multiplier"]}
    if worker["use_active_difficulty"] == True:
        header["min_multiplier"] = get_difficulty()
    else:
        header["min_multiplier"] = 1.0
    return header

#Listen /request_work
@app.route('/request_work', methods=['GET', 'POST'])
def request_work():
    #request transactions
    data = request.get_json()
    #global fee

    #check if user and worker transaction are present
    if "user_transaction" in data:
        user = data.get("user_transaction")
    else:
        print ("User transaction missing")
        return {"Error": "User transaction missing"}

    if "worker_transaction" in data:
        worker = data.get("worker_transaction")
    else:
        print ("Worker transaction missing")
        return {"Error": "Worker transaction missing"}

    #Read transaction and check if is valid
    user_block = block_create(user.get('block_type'), user.get('account').replace("xrb_", "nano_"), user.get('representative'), user.get('previous'), user.get("link_as_account"), int(user.get('balance')), user.get("signature"))
    if user_block == "invalid":
        print ("Invalid user transaction")
        return '{"Error": "Invalid user transaction"}'
    worker_block = block_create(worker.get('block_type'), worker.get('account').replace("xrb_", "nano_"), worker.get('representative'), worker.get('previous'), worker.get("link_as_account"), int(worker.get('balance')), worker.get("signature"))
    if worker_block == "invalid":
        print ("Invalid worker transaction")
        return {"Error": "Invalid worker transaction"}

    #If account source in both transactions is different
    if user_block.account != worker_block.account :
        print ("Different source accounts ")
        return '{"Error": "Different Accounts source"}'

    #If worker account is wrong
    if worker_block.link_as_account != worker["account"]:
        print("Worker account is incorrect")
        return {"Error": "Worker account is incorrect"}

    #Check if previous block in worker hash is correct
    if worker_block.previous != user_block.block_hash:
        print ("Incorrect previous block in worker block")
        return {"Error": "Incorrect previous block in worker block" }

    #Recalculate the Fee with active_difficulty with 10% tolerance
    if worker["use_active_difficulty"] == True:
        multiplier = get_difficulty()
        if (multiplier > worker["max_multiplier"]):
            return {"Error": "Maximum difficulty exceded"}
        else:
            print ("Using active difficulty: " + str(multiplier))
        if multiplier * 0.9 > 1.0:
            worker["fee"] *= (multiplier * 0.9) #multiplier fee with tolerance
        else:
            worker["fee"] *= 1.0
    else:
        multiplier = 1.0

    #Check if fee is right
    user_fee = user_block.balance - worker_block.balance
    if user_fee < worker["fee"]:
        print ( "Fee " + str(user_fee) + " is less than minimum " + str(worker["fee"]))
        return {"Error": "Fee is less than minimum"}

    #Check previous block
    if frontier(user_block.account) == user_block.previous:
        print ("Block is valid: " + user_block.block_hash)
    else:
        print ("Gap previous block")
        return {"Error": "Gap previous block"}

    #Check if account source has sufficient funds for both transactions
    if balance(user_block.account) < int(worker_block.balance):
        print ("Insufficient funds")
        return {"Error": "Insuficient funds"}
    else:
        print ("Account has sufficient funds")

    #If all is right, check active_difficulty and PoW both transactions
    print ("Solving Works...")
    user_block.work = solve_work(user_block.previous, multiplier)
    print ("User transaction: work done")
    worker_block.work = solve_work(worker_block.previous, multiplier)
    print ("Worker transaction: work done")

    #Broadcast
    r_user = broadcast(user_block.json())
    r_worker = broadcast(worker_block.json())

    #response
    if 'hash' in r_user:
        print ("User transaction successful! Block:" + r_user.get("hash"))
        response = {"Successful": r_user["hash"]}

        if 'hash' in r_worker:
            print ("Worker transaction successful! Block:" + r_worker["hash"])
            print ("Your reward has arrived!")
        else:
            print ("Worker transaction fail. Details: " + json.dumps(r_worker))
    else:
        print ("User transaction fail. Details: " + json.dumps(r_user) + "\n")
        response = {"Error": "User transaction fail. Details: " + json.dumps(r_user)}

    print ("\n")
    return response

#Serving API
waitress.serve(app, host='0.0.0.0', port=worker["service_port"])
