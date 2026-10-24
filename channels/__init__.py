"""
Omni-Channel Messaging Hub for Brigade & MAX.
Provides unified inbound pipeline with pairing challenges, deduplication,
abort triggers, and adapters for Telegram, Discord, Slack, WhatsApp, and BlueBubbles.
"""
from channels.base import BaseChannelAdapter, ChannelMessage, InboundResult
from channels.inbound_pipeline import InboundPipeline

__all__ = ["BaseChannelAdapter", "ChannelMessage", "InboundResult", "InboundPipeline"]
