import re
from typing import Any, Dict, List, Optional
import time
import asyncpg
import datetime

IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$")  # opcional: permite schema.table

def _ident(name: str) -> str:
    """Valida nombres de tabla/campo para prevenir inyección en identificadores."""
    if not isinstance(name, str) or not IDENT_RE.match(name):
        raise ValueError(f"Identificador inválido: {name!r}")
    # Si quieres preservar mayúsculas/minúsculas exactas, podrías comillar aquí.
    return name

def _order(order: str) -> str:
    order = (order or "ASC").upper()
    if order not in ("ASC", "DESC"):
        raise ValueError("ORDER inválido")
    return order

# ===== Pool global opcional (inícialo en startup de tu app) =====
_pool: Optional[asyncpg.Pool] = None

async def init_db_pool(dsn: str, min_size: int = 1, max_size: int = 10):
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn, min_size=min_size, max_size=max_size)

async def close_db_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def get_pool() -> asyncpg.Pool:
    assert _pool is not None, "Pool no inicializado: llama init_db_pool() primero"
    return _pool

class AsyncPGORM:
    
    async def exists(self, table: str, field: str, value) -> bool:
        """
        Verifica si un registro existe en la tabla dada.
        """
        tbl, fld = _ident(table), _ident(field)
        query = f'SELECT 1 FROM {tbl} WHERE {fld} = $1 LIMIT 1'
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(query, value)
            return row is not None
    
    async def get(self, table_name: str, field: str, value) -> Optional[Dict[str, Any]]:
        """
        Obtiene un registro de la tabla dada.
        """
        tbl, fld = _ident(table_name), _ident(field)
        sql = f'SELECT * FROM {tbl} WHERE {fld} = $1 LIMIT 1'
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(sql, value)
            return dict(row) if row else None
    
    async def get_one_specific_values(self, table_name: str, field: str, value, specific_fields: List[str]) -> Optional[Dict[str, Any]]:
        """
        Obtiene un registro de la tabla dada con campos específicos.
        
        Ejemplo:
            result = await orm.get_one_specific_values(
                table_name="users",
                field="id",
                value=123,
                specific_fields=["name", "email"]
            )
        Returns:
            dict: Un diccionario con los campos solicitados o None si no se encuentra el registro.
        """
        tbl, fld = _ident(table_name), _ident(field)
        cols = ", ".join(_ident(c) for c in specific_fields)
        sql = f'SELECT {cols} FROM {tbl} WHERE {fld} = $1 LIMIT 1'
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(sql, value)
            return dict(row) if row else None
    
    async def create(self, table_name: str, data: Dict[str, Any]) -> Optional[int]:
        """
        Crea un nuevo registro en la tabla dada.
        Retorna el ID del nuevo registro si la tabla tiene una columna 'id' autoincremental.
        """
        tbl = _ident(table_name)
        keys = list(data.keys())
        for k in keys: _ident(k)
        cols = ", ".join(keys)
        placeholders = ", ".join(f"${i+1}" for i in range(len(keys)))
        sql = f'INSERT INTO {tbl} ({cols}) VALUES ({placeholders}) RETURNING id'
        async with get_pool().acquire() as conn:
            row = await conn.fetchrow(sql, *[data[k] for k in keys])
            return row["id"] if row else None
    
    async def update(self, table_name: str, field: str, value, data: Dict[str, Any]) -> bool:
        tbl, fld = _ident(table_name), _ident(field)
        keys = list(data.keys())
        for k in keys: _ident(k)
        set_clause = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(keys))
        sql = f'UPDATE {tbl} SET {set_clause} WHERE {fld} = ${len(keys)+1}'
        params = [data[k] for k in keys] + [value]
        async with get_pool().acquire() as conn:
            await conn.execute(sql, *params)
        return True

    async def delete(self, table_name: str, field: str, value) -> bool:
        tbl, fld = _ident(table_name), _ident(field)
        sql = f'UPDATE {tbl} SET is_deleted = TRUE WHERE {fld} = $1'
        async with get_pool().acquire() as conn:
            await conn.execute(sql, value)
        return True
    
    