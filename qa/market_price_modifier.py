import requests
import json
import time
from copy import deepcopy
from collections import OrderedDict
from test_framework.test_framework import OpenBazaarTestFramework, TestFailure


class MarketPriceModifierTest(OpenBazaarTestFramework):

    def __init__(self):
        super().__init__()
        self.num_nodes = 2
        self.price_modifier = 10.25

    def run_test(self):
        vendor = self.nodes[0]
        buyer = self.nodes[1]

        # generate some coins and send them to buyer
        time.sleep(4)
        api_url = buyer["gateway_url"] + "wallet/address"
        r = requests.get(api_url)
        if r.status_code == 200:
            resp = json.loads(r.text)
            address = resp["address"]
        elif r.status_code == 404:
            raise TestFailure("MarketPriceModifierTest - FAIL: Address endpoint not found")
        else:
            raise TestFailure("MarketPriceModifierTest - FAIL: Unknown response")
        self.send_bitcoin_cmd("sendtoaddress", address, 10)
        time.sleep(20)

        # post profile for vendor
        with open('testdata/profile.json') as profile_file:
            profile_json = json.load(profile_file, object_pairs_hook=OrderedDict)
        api_url = vendor["gateway_url"] + "ob/profile"
        requests.post(api_url, data=json.dumps(profile_json, indent=4))

        # post listings to vendor
        with open('testdata/listing_crypto.json') as listing_file:
            listing_json = json.load(listing_file, object_pairs_hook=OrderedDict)
            listing_json_with_modifier = deepcopy(listing_json)
            listing_json_with_modifier["metadata"]["priceModifier"] = self.price_modifier

        api_url = vendor["gateway_url"] + "ob/listing"
        r = requests.post(api_url, data=json.dumps(listing_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("MarketPriceModifierTest - FAIL: Listing post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("MarketPriceModifierTest - FAIL: Listing POST failed. Reason: %s", resp["reason"])
        slug = json.loads(r.text)["slug"]

        api_url = vendor["gateway_url"] + "ob/listing"
        r = requests.post(api_url, data=json.dumps(listing_json_with_modifier, indent=4))
        if r.status_code == 404:
            raise TestFailure("MarketPriceModifierTest - FAIL: Listing post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("MarketPriceModifierTest - FAIL: Listing POST failed. Reason: %s", resp["reason"])
        slug_with_modifier = json.loads(r.text)["slug"]

        # get listing hashes
        api_url = vendor["gateway_url"] + "ipns/" + vendor["peerId"] + "/listings.json"
        r = requests.get(api_url)
        if r.status_code != 200:
            raise TestFailure("MarketPriceModifierTest - FAIL: Couldn't get listing index")
        resp = json.loads(r.text)
        listing_id = resp[0]["hash"]
        listing_id_with_modifier = resp[1]["hash"]

        # buyer send orders
        with open('testdata/order_crypto.json') as order_file:
            order_json = json.load(order_file, object_pairs_hook=OrderedDict)
        order_json["items"][0]["listingHash"] = listing_id
        api_url = buyer["gateway_url"] + "ob/purchase"
        r = requests.post(api_url, data=json.dumps(order_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("MarketPriceModifierTest - FAIL: Purchase post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("MarketPriceModifierTest - FAIL: Purchase POST failed. Reason: %s", resp["reason"])
        resp = json.loads(r.text)
        payment_address = resp["paymentAddress"]
        payment_amount = resp["amount"]
 
        with open('testdata/order_crypto.json') as order_file:
            order_json = json.load(order_file, object_pairs_hook=OrderedDict)
        order_json["items"][0]["listingHash"] = listing_id_with_modifier
        api_url = buyer["gateway_url"] + "ob/purchase"
        r = requests.post(api_url, data=json.dumps(order_json, indent=4))
        if r.status_code == 404:
            raise TestFailure("MarketPriceModifierTest - FAIL: Purchase post endpoint not found")
        elif r.status_code != 200:
            resp = json.loads(r.text)
            raise TestFailure("MarketPriceModifierTest - FAIL: Purchase POST failed. Reason: %s", resp["reason"])
        resp = json.loads(r.text)
        payment_address_with_modifier = resp["paymentAddress"]
        payment_amount_with_modifier = resp["amount"]

        # Check that modified price is different than regular price
        pct_change = round((payment_amount-payment_amount_with_modifier) / payment_amount * -100, 2)
        if pct_change != self.price_modifier:
            raise TestFailure("MarketPriceModifierTest - FAIL: Incorrect price modification: wanted %f but got %f", self.price_modifier, pct_change)

        print("MarketPriceModifierTest - PASS")

if __name__ == '__main__':
    print("Running MarketPriceModifierTest")
    MarketPriceModifierTest().main(["--regtest"])
