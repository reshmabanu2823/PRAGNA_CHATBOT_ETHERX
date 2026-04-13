"""Background scheduler for RAG knowledge base updates.

Automatically updates RAG with fresh content at regular intervals
to keep knowledge current beyond the model's training date.

Features:
- Scheduled updates at configured intervals
- Fetches latest news and information
- Runs in background thread
- Error recovery and retry logic
- Update logging and monitoring
"""
import logging
import threading
import time
from typing import Optional, Callable
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)


class RAGUpdateScheduler:
    """Scheduler for automated RAG knowledge base updates."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.enabled = config.RAG_AUTO_UPDATE_ENABLED
        self.update_interval = config.RAG_UPDATE_INTERVAL_HOURS * 3600  # Convert to seconds
        self.update_thread: Optional[threading.Thread] = None
        self.running = False
        self.last_update_time: Optional[datetime] = None
        self.update_count = 0
        self.update_errors = 0
        
        logger.info(
            f"🔄 RAG Update Scheduler initialized "
            f"(enabled: {self.enabled}, interval: {config.RAG_UPDATE_INTERVAL_HOURS}h)"
        )
    
    def start(self):
        """Start the background scheduler."""
        if not self.enabled:
            logger.debug("RAG auto-updates disabled in config")
            return
        
        if self.running:
            logger.warning("Scheduler already running")
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        logger.info("✅ RAG Update Scheduler started")
    
    def stop(self):
        """Stop the background scheduler."""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        logger.info("🛑 RAG Update Scheduler stopped")
    
    def _update_loop(self):
        """Main update loop running in background thread."""
        logger.info("📰 RAG updater thread started")
        ran_startup_update = False

        if config.RAG_RUN_IMMEDIATE_ON_START:
            logger.info("🚀 Running immediate startup RAG refresh")
            self._do_update()
            ran_startup_update = True
        else:
            # Wait for configured start hour on first run
            self._wait_for_start_time()
        
        while self.running:
            try:
                # If startup update already ran, wait full interval before the next cycle.
                if ran_startup_update:
                    logger.debug(f"Next update in {config.RAG_UPDATE_INTERVAL_HOURS} hours")
                    time.sleep(self.update_interval)
                    ran_startup_update = False

                # Perform update
                self._do_update()
                
                # Wait for next update
                logger.debug(f"Next update in {config.RAG_UPDATE_INTERVAL_HOURS} hours")
                time.sleep(self.update_interval)
            
            except Exception as e:
                logger.error(f"Error in update loop: {e}", exc_info=True)
                self.update_errors += 1
                # Wait before retry
                time.sleep(60)
    
    def _wait_for_start_time(self):
        """Wait until configured start hour."""
        try:
            start_hour = int(config.RAG_UPDATE_START_HOUR)
            
            now = datetime.now()
            target = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            
            # If time has passed today, start tomorrow
            if target <= now:
                target += timedelta(days=1)
            
            wait_seconds = (target - now).total_seconds()
            
            logger.info(
                f"⏰ Waiting until {target.strftime('%H:%M')} to start updates "
                f"({int(wait_seconds / 3600)}h {int((wait_seconds % 3600) / 60)}m)"
            )
            
            time.sleep(wait_seconds)
        
        except Exception as e:
            logger.warning(f"Error calculating start time: {e}, starting immediately")
    
    def _do_update(self):
        """Perform the actual RAG update."""
        logger.info("🔄 Starting RAG knowledge base update...")
        
        try:
            from services.rag_service import get_rag_service
            from services.web_scraper import update_rag_with_latest_news
            
            rag = get_rag_service()
            
            # Check if RAG is available
            if not rag.enabled:
                logger.warning("RAG not enabled, skipping update")
                return
            
            # Optional: Clear old documents first
            if config.RAG_CLEAR_BEFORE_UPDATE:
                logger.info("🧹 Clearing old documents...")
                rag.clear_index()
            
            # Add latest news
            success = update_rag_with_latest_news(max_articles=config.RAG_UPDATE_BATCH_SIZE)
            
            if success:
                self.last_update_time = datetime.now()
                self.update_count += 1
                
                stats = rag.get_stats()
                logger.info(
                    f"✅ RAG update completed successfully | "
                    f"Documents: {stats['document_count']} | "
                    f"Total updates: {self.update_count}"
                )
            else:
                logger.warning("⚠️ RAG update completed but with warnings")
                self.update_errors += 1
        
        except Exception as e:
            logger.error(f"❌ Error during RAG update: {e}", exc_info=True)
            self.update_errors += 1
    
    def get_status(self) -> dict:
        """Get scheduler status."""
        return {
            'enabled': self.enabled,
            'running': self.running,
            'update_interval_hours': config.RAG_UPDATE_INTERVAL_HOURS,
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'update_count': self.update_count,
            'update_errors': self.update_errors,
            'next_update_in_hours': (
                config.RAG_UPDATE_INTERVAL_HOURS - 
                int((datetime.now() - self.last_update_time).total_seconds() / 3600)
                if self.last_update_time else 'pending'
            )
        }
    
    def force_update(self) -> bool:
        """Force an immediate update (useful for testing/admin)."""
        if not self.enabled:
            logger.warning("Updates not enabled")
            return False
        
        logger.info("🚀 Forcing immediate RAG update...")
        try:
            self._do_update()
            return True
        except Exception as e:
            logger.error(f"Error forcing update: {e}")
            return False


# Global scheduler instance
_scheduler: Optional[RAGUpdateScheduler] = None


def get_rag_update_scheduler() -> RAGUpdateScheduler:
    """Get singleton scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = RAGUpdateScheduler()
    return _scheduler


def start_scheduler():
    """Start the background scheduler."""
    scheduler = get_rag_update_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler = get_rag_update_scheduler()
    scheduler.stop()


def get_scheduler_status() -> dict:
    """Get current scheduler status."""
    scheduler = get_rag_update_scheduler()
    return scheduler.get_status()


def force_rag_update() -> bool:
    """Force an immediate RAG update."""
    scheduler = get_rag_update_scheduler()
    return scheduler.force_update()
