import sys
import pandas as pd
import logging

sys.path.append('./')
sys.path.append('../')
from merchant_sdk.api import KafkaApi, PricewarsRequester
import os
import base64
import hashlib
import sys
import numpy as np


def download_data_and_aggregate(merchant_token):
    # Dont know, if we need that URL at some point
    # 'http://vm-mpws2016hp1-05.eaalab.hpi.uni-potsdam.de:8001'
    PricewarsRequester.add_api_token(merchant_token)
    logging.debug('Downloading files from Kafka ...')
    kafka_url = os.getenv('PRICEWARS_KAFKA_REVERSE_PROXY_URL', 'http://127.0.0.1:8001')
    kafka_api = KafkaApi(host=kafka_url)
    csvs = {'marketSituation': None, 'buyOffer': None}
    for topic in ['marketSituation', 'buyOffer']:
        try:
            data_url = kafka_api.request_csv_export_for_topic(topic)
            # TODO do we really need panda? Isnt the standard csv reader sufficient?
            csvs[topic] = pd.read_csv(data_url)
        except pd.io.common.EmptyDataError as e:
            logging.warning('Kafka returned an empty csv for topic {}'.format(topic))
        except Exception as e:
            logging.warning('Could not download data for topic {} from kafka: {}'.format(topic, e))
    logging.debug('Download finished')
    joined = aggregate(csvs, merchant_token)
    return joined


def aggregate(csvs, token):
    # Method stole from eyample MLmerchant
    """
    aggregate is going to transform the downloaded two csv it into a suitable data format, based on:
        $timestamp_1, $merchant_id_1, $product_id, $quality, $price
        $timestamp_1, $product_id, $sku, $price

        $timestamp_1, $sold_yes_no, $own_price, $own_price_rank, $cheapest_competitor, $best_competitor_quality
    :return:
    """
    joined_situations = dict()
    situation = csvs['marketSituation']
    sales = csvs['buyOffer']

    # If csvs are empty
    if not situation.empty and not sales.empty:
        return joined_situations

    own_sales = sales[sales['http_code'] == 200].copy()
    own_sales.loc[:, 'timestamp'] = match_timestamps(situation['timestamp'], own_sales['timestamp'])
    merchant_id = calculate_merchant_id_from_token(token)

    logging.debug('Aggregating data')

    for product_id in np.unique(situation['product_id']):
        ms_df_prod = situation[situation['product_id'] == product_id]

        dict_array = []
        for timestamp, group in ms_df_prod.groupby('timestamp'):
            features = extract_features_from_offer_snapshot(group, merchant_id)
            features.update({
                'timestamp': timestamp,
                'sold': own_sales[own_sales['timestamp'] == timestamp]['amount'].sum(),
            })
            dict_array.append(features)

        joined_situations[product_id] = dict_array
    logging.debug('Finished data aggregation')
    return joined_situations


def calculate_merchant_id_from_token(token):
    return base64.b64encode(hashlib.sha256(
        token.encode('utf-8')).digest()).decode('utf-8')


def match_timestamps(continuous_timestamps, point_timestamps):
    # WHAT ???
    t_ms = pd.DataFrame({
        'timestamp': continuous_timestamps,
        'origin': np.zeros((len(continuous_timestamps)))
    })
    t_bo = pd.DataFrame({
        'timestamp': point_timestamps,
        'origin': np.ones((len(point_timestamps)))
    })

    t_combined = pd.concat([t_ms, t_bo], axis=0).sort_values(by='timestamp')
    original_locs = t_combined['origin'] == 1

    t_combined.loc[original_locs, 'timestamp'] = np.nan
    # pad: propagates last marketSituation timestamp to all following (NaN) buyOffers
    t_padded = t_combined.fillna(method='pad')

    return t_padded[original_locs]['timestamp']


def extract_features_from_offer_snapshot(offers_df, merchant_id, product_id=None):
    if product_id:
        offers_df = offers_df[offers_df['product_id'] == product_id]
    competitors = offers_df[offers_df['merchant_id'] != merchant_id]
    own_situation = offers_df[offers_df['merchant_id'] == merchant_id]
    has_offer = len(own_situation) > 0
    has_competitors = len(competitors) > 0

    if has_offer:
        own_offer = own_situation.sort_values(by='price').iloc[0]
        own_price = own_offer['price']
        own_quality = own_offer['quality']
        price_rank = 1 + (offers_df['price'] < own_price).sum() + ((offers_df['price'] == own_price).sum()/2)
        distance_to_cheapest_competitor = float(own_price - competitors['price'].min()) if has_competitors else np.nan
        quality_rank = (offers_df['quality'] < own_quality).sum() + 1
    else:
        own_price = np.nan
        price_rank = np.nan
        distance_to_cheapest_competitor = np.nan
        quality_rank = np.nan

    amount_of_all_competitors = len(competitors)
    average_price_on_market = offers_df['price'].mean()
    return {
        'own_price': own_price,
        'price_rank': price_rank,
        'distance_to_cheapest_competitor': distance_to_cheapest_competitor,
        'quality_rank': quality_rank,
        'amount_of_all_competitors': amount_of_all_competitors,
        'average_price_on_market': average_price_on_market
    }
