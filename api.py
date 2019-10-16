from flask import Flask, jsonify, request
from functions import block_create, check_balance, check_block, broadcast, worker_account, minimum_fee
from nanolib import Block

import requests
import json

app = Flask(__name__)


@app.route('/open_request', methods=['GET', 'POST'])
def opening_request():
    return {
	"reward_address": worker_account,
 	"minimum_fee": minimum_fee,
    }


@app.route('/request_pow', methods=['GET', 'POST'])
def request_pow():

    #request transactions
    data = request.get_json()

    #check if user and worker transaction are present
    if "user_transaction" in data:
        user = data.get("user_transaction")
    else:
        print ("User transaction missing")
        return {"Error": "User transaction missing"}

    if "user_transaction" in data:
        worker = data.get("worker_transaction")
    else:
        print ("Worker transaction missing")
        return {"Error": "Worker transaction missing"}


    #Read transaction and check if is valid
    user_block = block_create(user.get('block_type'), user.get('account'), user.get('representative'), user.get('previous'), user.get("link_as_account"), user.get("signature"), int(user.get('balance')))
    if user_block == "invalid":
        print ("Invalid user transaction")
        return '{"Error": "Invalid user transaction"}'
    worker_block = block_create(worker.get('block_type'), worker.get('account'), worker.get('representative'), worker.get('previous'), worker.get("link_as_account"), worker.get("signature"), int(worker.get('balance')))
    if worker_block == "invalid":
        print ("Invalid worker transaction")
        return {"Error": "Invalid worker transaction"}

    #If account source in both transactions is different
    if user_block.account != worker_block.account :
        print ("Different source accounts ")
        return '{"Error": "Different Accounts source"}'

    #If worker account is wrong
    if worker_block.link_as_account != worker_account:
        print("Worker account is incorrect")
        return {"Error": "Worker account is incorrect"}


    #Check if previous block in worker hash is correct
    if worker_block.previous != user_block.block_hash:
        print ("Incorrect previous block in worker block")
        return {"Error": "Incorrect previous block in worker block" }

    #Check if fee is right
    fee = user_block.balance - worker_block.balance
    if fee  < minimum_fee:
        print ( "Fee " + str(fee) + " is less than minimum " + str(minimum_fee))
        return {"Error": "Fee " + str(fee) + " is less than minimum " + str(minimum_fee)}

    #Check if user block already exists
    if check_block(user_block.block_hash) == "exists":
        print ("User block already exists")
        return {"Error": "User block already exists"}

    #Check if account source has sufficient funds for both transactions
    if check_balance(user_block.account, int(worker_block.balance)) is False:
        print ("Insufficient funds")
        return {"Error": "Insuficient funds"}
    else:
        print ("Account has sufficient funds")


    #If all is right, PoW both transactions
    user_block.solve_work()
    print ("User transaction: work done")
    worker_block.solve_work()
    print ("Worker transaction: work done")


    #Broadcast
    r_user = broadcast(user_block.json())
    r_worker = broadcast(worker_block.json())


    #response
    if 'hash' in r_user:
        print ("User transaction successful! Block:" + r_user.get("hash") + "\n")
        response = {"Successful": r_user["hash"]}

        if 'hash' in r_worker:
            print ("Worker transaction successful! Block:" + r_user["hash"] + "\n")
        else:
            print ("Worker transaction fail. Details: " + json.dumps(r_worker) + "\n")

    else:
        print ("User transaction fail. Details: " + json.dumps(r_user) + "\n")
        response = {"Error": "User transaction fail. Details: " + json.dumps(r_user)}

    return response
