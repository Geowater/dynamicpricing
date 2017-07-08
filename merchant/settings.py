import os

from merchant_sdk import MerchantBaseLogic


class Settings:
    def __init__(self, data_file, merchant_token='0hjzYcmGQUKnCjtHKki3UN2BvMJouLBu2utbWgqwBBkNuefFOOJslK4hgOWbihWl'):
        if os.getenv('API_TOKEN'):
            self.merchant_token = os.getenv('API_TOKEN')
        else:
            self.merchant_token = merchant_token
        self.merchant_id = MerchantBaseLogic.calculate_id(self.merchant_token)
        self.initial_merchant_id = 'DaywOe3qbtT3C8wBBSV+zBOH55DVz40L6PH1/1p9xCM='
        self.marketplace_url = MerchantBaseLogic.get_marketplace_url()
        self.producer_url = MerchantBaseLogic.get_producer_url()
        self.kafka_reverse_proxy_url = MerchantBaseLogic.get_kafka_reverse_proxy_url()
        self.debug = True
        self.max_amount_of_offers = 10
        self.shipping = 2
        self.primeShipping = 1
        self.max_req_per_sec = 10.0
        self.learning_interval = 2.0
        self.data_file = ('../tmp/' + data_file) if data_file is not None else None
        self.underprice = 0.2
        self.initialProducts = 5
