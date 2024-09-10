import json
import pyjq
import logging
from app.services.gundi import send_observations_to_gundi, send_events_to_gundi
from app.services.activity_logger import webhook_activity_logger
from .configurations import BinaryWebhookPayload, BinaryWebhookConfig


logger = logging.getLogger(__name__)


@webhook_activity_logger()
async def webhook_handler(payload: BinaryWebhookPayload, integration=None, webhook_config: BinaryWebhookConfig = None):
    logger.info(f"Webhook handler executed with integration: '{integration}'.")
    logger.info(f"Payload: '{payload}'.")
    logger.info(f"Config: '{webhook_config}'.")
    if isinstance(payload, list):
        input_data = [json.loads(i.json()) for i in payload]
    else:
        input_data = json.loads(payload.json())

    filter_expression = webhook_config.jq_filter.replace("\n", "")
    transformed_data = pyjq.all(filter_expression, input_data)
    logger.info(f"Transformed Data: {transformed_data}")
    # Check if a filter is present in the filtered data
    for data in transformed_data:
        status = data.get("status", "OK")
        if status != "OK":
            logger.info(f"'{data}' point received was filtered")
            transformed_data.remove(data)
    if transformed_data:
        # Make binary operations (Sigfox Trackers for now)
        # TODO: make this more generic
        for data in transformed_data:
            # Latitude operations
            latitude_sign = data["location"].get("latitude_sign")
            if latitude_sign == "8": # Negative indicator (Provided by sigfox)
                latitude_sign = -1
            else:
                latitude_sign = 1
            latitude_to_decimal = (round(((int(data["location"].get("latitude"), 16)) / 1000000), 3)) * latitude_sign

            # Longitude operations
            longitude_sign = data["location"].get("longitude_sign")
            if longitude_sign == "8": # Negative indicator (Provided by sigfox)
                longitude_sign = -1
            else:
                longitude_sign = 1
            longitude_to_decimal = (round(((int(data["location"].get("longitude"), 16)) / 1000000), 3)) * longitude_sign

            # Replace location data
            data["location"] = dict(lat=latitude_to_decimal, lon=longitude_to_decimal)

            # Calculate battery voltage in 'additional'
            data["additional"]["battery"] = int(data["additional"].get("battery"), 16) / 10


        if webhook_config.output_type == "obv":  # ToDo: Use an enum?
            response = await send_observations_to_gundi(
                observations=transformed_data,
                integration_id=integration.id
            )
        elif webhook_config.output_type == "ev":
            response = await send_events_to_gundi(
                events=transformed_data,
                integration_id=integration.id
            )
        else:
            raise ValueError(f"Invalid output type: {webhook_config.output_type}. Please review the configuration.")
        data_points_qty = len(response)
        logger.info(f"'{data_points_qty}' data point(s) sent to Gundi.")
        return {"data_points_qty": data_points_qty}
    else:
        logger.info(f"No data point(s) sent to Gundi.")
        return {"data_points_qty": 0}
