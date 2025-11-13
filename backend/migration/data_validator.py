#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Validator for CSV Migration.

Validates data before inserting into PostgreSQL database.
Handles missing data, type conversion, and data integrity checks.
"""

import re
import json
from typing import Optional, Any
from datetime import datetime

import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates data before database insertion."""
    
    # ASIN pattern: 10 characters, alphanumeric
    ASIN_PATTERN = re.compile(r'^[A-Z0-9]{10}$')
    
    # Email pattern
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def validate_asin(self, asin: Optional[str]) -> Optional[str]:
        """
        Validate ASIN format.
        
        Args:
            asin: ASIN string to validate
            
        Returns:
            Validated ASIN if valid, None otherwise
            
        Examples:
            >>> validator = DataValidator()
            >>> validator.validate_asin("B08EXAMPLE")
            'B08EXAMPLE'
            >>> validator.validate_asin("invalid")
            None
        """
        if not asin:
            return None
        
        asin = str(asin).strip().upper()
        
        if len(asin) != 10:
            logger.warning(f"Invalid ASIN length: {asin}")
            return None
        
        if not self.ASIN_PATTERN.match(asin):
            logger.warning(f"Invalid ASIN format: {asin}")
            return None
        
        return asin
    
    def validate_string(
        self,
        value: Optional[Any],
        field_name: str,
        max_length: Optional[int] = None,
        allow_none: bool = False
    ) -> Optional[str]:
        """
        Validate string value.
        
        Args:
            value: Value to validate
            field_name: Name of field for error messages
            max_length: Maximum length allowed
            allow_none: Whether None is allowed
            
        Returns:
            Validated string or None
        """
        if value is None:
            if allow_none:
                return None
            logger.warning(f"Missing required field: {field_name}")
            return ""
        
        str_value = str(value).strip()
        
        if max_length and len(str_value) > max_length:
            logger.warning(f"Field {field_name} exceeds max length {max_length}, truncating")
            str_value = str_value[:max_length]
        
        return str_value if str_value else (None if allow_none else "")
    
    def validate_int(
        self,
        value: Optional[Any],
        field_name: str,
        default: int = 0,
        allow_none: bool = False,
        min_value: Optional[int] = None,
        max_value: Optional[int] = None
    ) -> Optional[int]:
        """
        Validate integer value.
        
        Args:
            value: Value to validate
            field_name: Name of field for error messages
            default: Default value if None
            allow_none: Whether None is allowed
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated integer or None
        """
        if value is None:
            if allow_none:
                return None
            return default
        
        try:
            int_value = int(float(str(value)))
            
            if min_value is not None and int_value < min_value:
                logger.warning(f"Field {field_name} value {int_value} below minimum {min_value}")
                return min_value
            
            if max_value is not None and int_value > max_value:
                logger.warning(f"Field {field_name} value {int_value} above maximum {max_value}")
                return max_value
            
            return int_value
            
        except (ValueError, TypeError):
            logger.warning(f"Invalid integer value for {field_name}: {value}, using default {default}")
            return default if not allow_none else None
    
    def validate_float(
        self,
        value: Optional[Any],
        field_name: str,
        default: float = 0.0,
        allow_none: bool = False,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None
    ) -> Optional[float]:
        """
        Validate float value.
        
        Args:
            value: Value to validate
            field_name: Name of field for error messages
            default: Default value if None
            allow_none: Whether None is allowed
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Validated float or None
        """
        if value is None:
            if allow_none:
                return None
            return default
        
        try:
            float_value = float(str(value))
            
            if min_value is not None and float_value < min_value:
                logger.warning(f"Field {field_name} value {float_value} below minimum {min_value}")
                return min_value
            
            if max_value is not None and float_value > max_value:
                logger.warning(f"Field {field_name} value {float_value} above maximum {max_value}")
                return max_value
            
            return float_value
            
        except (ValueError, TypeError):
            logger.warning(f"Invalid float value for {field_name}: {value}, using default {default}")
            return default if not allow_none else None
    
    def validate_email(self, email: Optional[str]) -> Optional[str]:
        """
        Validate email address.
        
        Args:
            email: Email string to validate
            
        Returns:
            Validated email if valid, None otherwise
        """
        if not email:
            return None
        
        email = str(email).strip().lower()
        
        if not self.EMAIL_PATTERN.match(email):
            logger.warning(f"Invalid email format: {email}")
            return None
        
        return email
    
    def validate_json(
        self,
        value: Optional[Any],
        allow_none: bool = True
    ) -> Optional[dict]:
        """
        Validate JSON value.
        
        Args:
            value: Value to validate as JSON
            allow_none: Whether None is allowed
            
        Returns:
            Validated dict or None
        """
        if value is None:
            return None if allow_none else {}
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON string: {value}")
                return {} if not allow_none else None
        
        # Try to convert to dict
        try:
            return dict(value)
        except (TypeError, ValueError):
            logger.warning(f"Could not convert to dict: {value}")
            return {} if not allow_none else None
    
    def validate_date(
        self,
        value: Optional[Any],
        field_name: str,
        allow_none: bool = True
    ) -> Optional[datetime]:
        """
        Validate date/datetime value.
        
        Args:
            value: Value to validate
            field_name: Name of field for error messages
            allow_none: Whether None is allowed
            
        Returns:
            Validated datetime or None
        """
        if value is None:
            return None if allow_none else datetime.utcnow()
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d',
                '%d/%m/%Y',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse date {value} for {field_name}")
            return None if allow_none else datetime.utcnow()
        
        return None if allow_none else datetime.utcnow()

