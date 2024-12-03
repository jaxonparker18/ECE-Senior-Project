from inference import get_roboflow_model

"""
Run this file to cache model onto machine.
"""

model_name = "deteksiasapdanapi"  # FIRE
model_version = "4"
api_key = "NHxBSfWHlHDOQC07yyLm"
model = get_roboflow_model(
    model_id="{}/{}".format(model_name, model_version),
    # Replace ROBOFLOW_API_KEY with your Roboflow API Key
    api_key=api_key
)