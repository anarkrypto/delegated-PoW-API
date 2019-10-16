# Delegated Proof of Work - API
Worker API for P2P delegated Proof of Work, Nano cryptocurrency

## Introduction

This project has the ability to make Nano instantaneous for any type of low computing device by delegating PoW to Workers on a P2P network, requiring no central servers / coordinators.

The only way a user can have their transaction completed by Worker is to attach an extra transaction block as a reward after their transactions. The only way for a Worker to receive his reward is by completing PoW and broadcasting the user's transaction first to be able to validate his reward block.

## Configuring
Edit the config.json file. Enter your account,the minimum fee you prefer for each job and your node address.
The fee is represented in raws (1 Nano / 10^30). 1000000000000000000000000 raws = 0.000001 Nano
Your node must be fully synchronized with the network
Example:


    {
	    "reward_address": "nano_3goufw1psaxsbqhuky3mcra74uz8ki7mkbb6rpupx1g87bsi4innftt4sckk",
 	    "minimum_fee": 1000000000000000000000000,
	    "node_url": "127.0.0.1:7076"
    }



## How to run (Unix systems)

    pip3 install -r requirements.txt
    export FLASK_APP=api.py
    flask run


## How to run (Windows)

    pip3 install -r requirements.txt
    set FLASK_APP=api.py
    flask run


## How it works

The user requests Workers confirmation at the endpoint localhost:5000/open_request
And get the following kind of answer:

      {
	      "reward_address": "nano_3goufw1psaxsbqhuky3mcra74uz8ki7mkbb6rpupx1g87bsi4innftt4sckk",
 	      "minimum_fee": 1000000000000000000000000
      }

This is the worker's reward address and his minimum rate per job. 
This rate must be multiplied by the (number of transactions sent - transaction reward)

Then users will use this information to sign the worker reward transaction.


Users can request the PoW by calling the endpoint (/request_pow) sending a json data like the following one:


        curl -s --header "Content-Type: application/json" --request POST --data '{
          "user_transaction": { "block_type": "state", 
            "account": "nano_1bca3mirn8aauzy5m5o984bfphsxsbwsixc47d535rkg75nbzd3w737n6iya", 
            "previous": "11B1CCBBD2CFDDF46D0DE6D96D447431940C79DC90EB4F10E8271CD1BBB43ABD", 
            "representative": "nano_1hza3f7wiiqa7ig3jczyxj5yo86yegcmqk3criaz838j91sxcckpfhbhhra1", 
            "balance": "1999999999999999999997172", 
            "link": "F4D9B075403D7325A9F0775B7FFE2E9B7AE14936AA953388949E1751DD996007", 
            "link_as_account": "nano_3x8sp3tn1hdm6pnz1xtuhzz4x8utw76mfcno8g6bb9iqc9gskr191tq8eaat", 
            "signature": "69CAEA32BC8E9CF8E47CF4453493929C6BDC11373FD4C228FDBE11A5D76F32A4FF5CFC5D7AD33A67CF3AE9014434B39CDFE83BB9F5F2BF08F5ED0EFBC391870D"
            },
        "worker_transaction": { 
          "block_type": "state", 
          "account": "nano_1bca3mirn8aauzy5m5o984bfphsxsbwsixc47d535rkg75nbzd3w737n6iya", 
          "previous": "1BD2525DE8E4E439A50322A04C77031D3D0F747C53839F20DB3716DEFC6E2D4D", 
          "representative": "nano_1hza3f7wiiqa7ig3jczyxj5yo86yegcmqk3criaz838j91sxcckpfhbhhra1", 
          "balance": "999999999999999999997172", 
          "link": "BABB6F016CA3B94DDFB978335610516FE6940B392524C5B76E81C62A73014294", 
          "link_as_account": "nano_3goufw1psaxsbqhuky3mcra74uz8ki7mkbb6rpupx1g87bsi4innftt4sckk", 
          "signature": "E40DD1FAB27161FF2DD73FAB20082A04F86632ECFC8FC60707D2B8221B1CFE7C3B01A8D718AC04C3F6F5EC764C8EBD9905CC756FE2DB381D81A0AC7D2A974D00"
          }
      }' localhost:5000/request_pow

 

The first transaction is the user_transaction. The second one (worker_transaction) is responsible for the payment of the worker. 


## Attention!!! 
This version is still mere Proof of Concept. Use for micro-transactions only.
