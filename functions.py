from nanolib import Block, get_account_id
import json
import requests

#Convert IP address to valid url format
def toURL(address):
    if not address.startswith("http"):
        return "http://" + address
    else:
        return address

#Import config
with open('worker_config.json') as worker_config:
    data = json.load(worker_config)
worker_account = data['reward_account'].replace("xrb_", "nano_")
worker_private_key = data['private_key']
worker_representative = data['representative'].replace("xrb_", "nano_")
min_fee = data['fee']
node = toURL(data['node'])
worker_node = toURL(data['worker'])
use_active_difficulty = data['use_active_difficulty']
max_multiplier = data['max_multiplier']
service_port = data['port']

with open('register_config.json') as register_config:
    data_register = json.load(register_config)
general_account = data_register['general_account'].replace("xrb_", "nano_")
sign_new_ip_code = int(data_register['sign_new_ip_code'])
sign_new_account_code = int(data_register['sign_new_account_code'])
get_ip = toURL(data_register['get_ip'])

#Read transaction Block
def block_create(block_type, account, representative, previous, link_as_account, balance, signature):
    try:
        block = Block(
            block_type=block_type,
            account=account,
            representative=representative,
            previous=previous,
            link_as_account=link_as_account,
            balance=balance,
        )
    except:
        return "invalid"
    else:
        if signature is not None:
            try:
                block.signature = signature
            except:
                return "invalid"
        return block

#check if the account has the balance
def balance(account):
    resp = requests.post(node, json={"action": "account_balance", "account": account})
    return int(resp.json()['balance'])

#account history
def check_history(account, destination):
    request = requests.post(node, json={"action": "account_history", "account": account, "count": -1})
    history = request.json()["history"]
    for b in history:
        if destination == b["account"].replace("xrb_", "nano_"):
            return b
    return (None)

#check if block already exists
def frontier(account):
     request = requests.post(node, json={"action": "accounts_frontiers", "accounts": [account]})
     if account in request.json()["frontiers"]:
        return request.json()["frontiers"][account]
     else:
        request = requests.post(node, json={ "action": "account_key", "account" : account })
        return request.json()["key"]

#active difficulty network
def get_difficulty():
     request = requests.post(node, json={"action": "active_difficulty", "include_trend": "true"})
     return float(request.json()["multiplier"])

#solve work
def solve_work (hash, multiplier):
     request = requests.post(worker_node, json={"action": "work_generate", "hash": hash, "multiplier": multiplier })
     return request.json()["work"]

#broadcast transaction
def broadcast(transaction):
    request = requests.post(node, json={"action": "process", "json_block": "true", "block": json.loads(transaction)})
    return request.json()

def pending_filter (account, threshold):
    request = requests.post(node, json={"action": "pending", "account": account, "count": "-1", "threshold": "1"})
    blocks = request.json()["blocks"]
    if blocks == "":
        return None
    else:
        if len(blocks) == 1:
            return blocks
        else:
            for key in blocks:
                    blocks[key] = int(blocks[key])
            sorted_blocks = sorted(blocks.items(), key=lambda kv: kv[1], reverse=True)
            for key in sorted_blocks:
                receive_blocks[key] = sorted_blocks[key]
                acumulated += sorted_blocks[key]
                if acumulated >= threshold:
                    return receive_blocks
            return None

def receive(account, private_key, representative, amount, link, difficulty):
     request = requests.post(node, json={"action": "accounts_frontiers", "accounts": [account]})
     if account in request.json()["frontiers"]:
        previous = request.json()["frontiers"][account]
     else:
         previous = "0000000000000000000000000000000000000000000000000000000000000000"
     block = Block(
        block_type="state",
        account=account,
        representative=representative,
        previous=previous,
        balance=balance(worker_account) + amount,
        link=link
     )
     block.work = solve_work(frontier(account), difficulty)
     block.sign(private_key)
     print (block.json())
     r = broadcast(block.json())
     return r


def send (account, representative, previous, link_as_account, amount, difficulty):
    block = block_create("state", account, representative, previous, link_as_account, balance(worker_account) - amount, None)
    block.sign(worker_private_key)
    block.work = solve_work(block.previous, difficulty)
    r = broadcast(block.json())
    return r

def check_key_pair(account, private_key):
    if account == get_account_id(private_key=private_key, prefix="nano_"):
        return True
    else:
        return False

def get_my_ip():
    myIP = requests.get(get_ip)
    return myIP.text

#encode IPv4 or IPv6 into Nano Account format
def encode_ip (ip):
    ip_as_bytes = bytes(map(int, ip.split('.'))) #convert to bytes
    ip_as_bytes += (32 - len(ip_as_bytes)) * b'\0' #padding
    ip_account =  get_account_id(public_key=ip_as_bytes.hex(), prefix="nano_") ##convert to nano account format
    return ip_account


def register (account, representative, previous, register_account, code, multiplier):
    if code == sign_new_account_code:
        what = "your worker account"
    if code == sign_new_ip_code:
        what = "your IP address"

    if balance(account) >= code:
        print ("You have sufficient funds to register " + what)
        print ("Registering " + what + " now")
        r = send(account, representative, previous, register_account, code, multiplier)
        if 'hash' in r:
            print ("Successfully registred " + what + " Block:" + r["hash"])
        else:
            print ("Register transaction fail. Details: " + json.dumps(r))
    else:
        print ("No funds detected, checking if exists unpocketed transactions...")
        pending = pending_filter(account, sign_new_account_code + sign_new_ip_code )
        if pending == None:
            print ("You have not sufficient funds to register " + what + "! Please send at least " + str((sign_new_account_code + sign_new_ip_code)) + " raws to your worker account")
        else:
            for block in pending:
                print ("Receiving pending block: " + str(pending[block]) + " raws")
                r = receive(account, worker_private_key, frontier(account), representative, int(pending[block]), block, multiplier)
                if 'hash' in r:
                    print ("Transaction received!" + " Block:" + r["hash"])
                else:
                    print ("Transaction receiving fail. Details: " + json.dumps(r))
            print ("Ok, registering " + what + " now")
            r = send(account, representative, frontier(account), register_account, code, multiplier)
            if 'hash' in r:
                print ("Successfully registred " + what + " Block:" + r["hash"])
            else:
                print ("Register transaction fail. Details: " + json.dumps(r))
