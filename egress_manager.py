import logging
import asyncio
from typing import Optional, Tuple
from livekit import api
from livekit.protocol.egress import RoomCompositeEgressRequest, EncodedFileOutput, S3Upload

logger = logging.getLogger("egress-manager")

class EgressManager:
    """
    Manages LiveKit Egress recordings.
    """
    
    def __init__(self, api_client):
        self.api = api_client

    async def start_room_composite_egress(
        self, 
        room_name: str, 
        layout: str = "speaker-light", 
        file_output_filepath: Optional[str] = None,
        s3_options: Optional[dict] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Starts a composite egress recording for the specified room.
        
        Args:
            room_name: The name of the room to record.
            layout: The layout to use (default: "speaker-light").
            file_output_filepath: Optional specific filepath/prefix for the output.
            s3_options: Optional dictionary containing S3 credentials (access_key, secret, bucket, region, endpoint).
            
        Returns:
            A tuple containing (egress_id, recording_url).
            egress_id is None if failed.
            recording_url is None if not constructible or failed.
        """
        try:
            file_output = EncodedFileOutput()
            file_output.file_type = api.EncodedFileType.MP4 # Explicitly set file type
    
            valid_s3 = False
            # Ensure critical S3 fields are present and non-empty
            if s3_options and s3_options.get("access_key") and s3_options.get("bucket") and s3_options.get("secret"):
                logger.info("Configuring S3 upload for egress")
                s3_upload = S3Upload(
                    access_key=s3_options.get("access_key"),
                    secret=s3_options.get("secret"),
                    bucket=s3_options.get("bucket"),
                    region=s3_options.get("region", ""),
                    endpoint=s3_options.get("endpoint", "")
                )
                file_output.s3.CopyFrom(s3_upload)
                valid_s3 = True
            else:
                logger.warning("S3 credentials not provided. Skipping egress recording to avoid failures.")
                return None, None
            
            # Always ensure a filepath (key) is set. 
            # If S3 is valid, this acts as the object key.
            # If S3 is invalid/missing, this is the filename (e.g. for generic storage).
            if not file_output_filepath:
                import datetime
                timestamp = int(datetime.datetime.now().timestamp())
                file_output.filepath = f"recording-{room_name}-{timestamp}.mp4"
            else:
                 file_output.filepath = file_output_filepath

            # Construct URL if S3 options are present
            recording_url = None
            if valid_s3:
                bucket = s3_options.get("bucket")
                endpoint = s3_options.get("endpoint")
                region = s3_options.get("region")
                key = file_output.filepath

                if endpoint:
                     # Clean up endpoint
                     if not endpoint.startswith("http"):
                         endpoint = f"https://{endpoint}"
                     recording_url = f"{endpoint.rstrip('/')}/{bucket}/{key}"
                else:
                     # AWS S3 standard
                     if region:
                        recording_url = f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
                     else:
                        recording_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            # Using 'file' (singular) as it is the standard oneof field for EncodedFileOutput.
            request = RoomCompositeEgressRequest(
                room_name=room_name,
                layout=layout,
                file_outputs=[file_output], 
            )
            
            response = await self.api.egress.start_room_composite_egress(request)
            egress_id = response.egress_id
            logger.info(f"🎥 Recording started. Egress ID: {egress_id}, URL: {recording_url}")
            return egress_id, recording_url
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            return None, None

    async def stop_egress(self, egress_id: str):
        """
        Stops an active egress recording.
        """
        try:
            request = api.StopEgressRequest(egress_id=egress_id)
            await self.api.egress.stop_egress(request)
            logger.info(f"⏹️ Recording stopped. Egress ID: {egress_id}")
        except Exception as e:
            logger.error(f"❌ Failed to stop recording {egress_id}: {e}")
