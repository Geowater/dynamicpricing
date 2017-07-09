import argparse
import logging

from sklearn.neural_network import MLPRegressor

from MlMerchant import MLMerchant
from merchant_sdk import MerchantServer
from settings import Settings


class MLPMerchant(MLMerchant):
    def __init__(self):
        self.model = dict()
        super().__init__(Settings.create('mlp_models.pkl'))

    def train_model(self, features):
        # TODO include time and amount of sold items to featurelist
        logging.debug('Start training')
        for product_id, vector_tuple in features.items():
            # More configuration needed here
            product_model = MLPRegressor(hidden_layer_sizes=(10,), max_iter=100000)
            # TODO: what does partial_fit() do?
            product_model.fit(vector_tuple[0], vector_tuple[1])
            self.model[product_id] = product_model
        logging.debug('Finished training')

    def predict(self, product_id, situations):
        # TODO: What happens if there is no such product_id ?
        # TODO2: It's possible, that predict return negative possibility,
        #        that's actually not possible
        return self.model[product_id].predict(situations)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    parser = argparse.ArgumentParser(
        description='PriceWars Merchant doing MLP Regression')
    parser.add_argument('--port',
                        type=int,
                        default=5103,
                        help='Port to bind flask App to, default is 5103')
    args = parser.parse_args()
    server = MerchantServer(MLPMerchant())
    app = server.app
    app.run(host='0.0.0.0', port=args.port)