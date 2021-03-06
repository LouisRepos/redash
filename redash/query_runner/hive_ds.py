import json
import logging
import sys

from redash.query_runner import *
from redash.utils import JSONEncoder

logger = logging.getLogger(__name__)

try:
    from pyhive import hive
    enabled = True
except ImportError:
    enabled = False

COLUMN_NAME = 0
COLUMN_TYPE = 1

types_map = {
    'BIGINT_TYPE': TYPE_INTEGER,
    'TINYINT_TYPE': TYPE_INTEGER,
    'SMALLINT_TYPE': TYPE_INTEGER,
    'INT_TYPE': TYPE_INTEGER,
    'DOUBLE_TYPE': TYPE_FLOAT,
    'DECIMAL_TYPE': TYPE_FLOAT,
    'FLOAT_TYPE': TYPE_FLOAT,
    'REAL_TYPE': TYPE_FLOAT,
    'BOOLEAN_TYPE': TYPE_BOOLEAN,
    'TIMESTAMP_TYPE': TYPE_DATETIME,
    'DATE_TYPE': TYPE_DATETIME,
    'CHAR_TYPE': TYPE_STRING,
    'STRING_TYPE': TYPE_STRING,
    'VARCHAR_TYPE': TYPE_STRING
}


class Hive(BaseSQLQueryRunner):
    noop_query = "SELECT 1"

    @classmethod
    def configuration_schema(cls):
        return {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string"
                },
                "port": {
                    "type": "number"
                },
                "database": {
                    "type": "string"
                },
                "username": {
                    "type": "string"
                }
            },
            "required": ["host"]
        }

    @classmethod
    def annotate_query(cls):
        return False

    @classmethod
    def type(cls):
        return "hive"

    @classmethod
    def enabled(cls):
        return enabled

    def __init__(self, configuration):
        super(Hive, self).__init__(configuration)

    def _get_tables(self, schema):
        try:
            schemas_query = "show schemas"

            tables_query = "show tables in %s"

            columns_query = "show columns in %s.%s"

            for schema_name in filter(lambda a: len(a) > 0, map(lambda a: str(a['database_name']), self._run_query_internal(schemas_query))):
                for table_name in filter(lambda a: len(a) > 0, map(lambda a: str(a['tab_name']), self._run_query_internal(tables_query % schema_name))):
                    columns = filter(lambda a: len(a) > 0, map(lambda a: str(a['field']), self._run_query_internal(columns_query % (schema_name, table_name))))

                    if schema_name != 'default':
                        table_name = '{}.{}'.format(schema_name, table_name)

                    schema[table_name] = {'name': table_name, 'columns': columns}
        except Exception as e:
            raise sys.exc_info()[1], None, sys.exc_info()[2]
        return schema.values()

    def run_query(self, query, user):

        connection = None
        try:
            connection = hive.connect(**self.configuration.to_dict())

            cursor = connection.cursor()

            cursor.execute(query)

            column_names = []
            columns = []

            for column in cursor.description:
                column_name = column[COLUMN_NAME]
                column_names.append(column_name)

                columns.append({
                    'name': column_name,
                    'friendly_name': column_name,
                    'type': types_map.get(column[COLUMN_TYPE], None)
                })

            rows = [dict(zip(column_names, row)) for row in cursor]

            data = {'columns': columns, 'rows': rows}
            json_data = json.dumps(data, cls=JSONEncoder)
            error = None
        except KeyboardInterrupt:
            connection.cancel()
            error = "Query cancelled by user."
            json_data = None
        finally:
            if connection:
                connection.close()

        return json_data, error

register(Hive)
