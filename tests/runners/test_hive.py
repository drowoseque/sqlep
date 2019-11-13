import pytest

from sqlep import run_test_query


def test_runner_connect_to_hive(hive, hive_cursor, hive_runner):
    # arrange & act
    run_test_query(
        query='',
        tables=dict(),
        expected=dict(),
        test_schema='',
        runner=hive_runner,
    )

    # assert
    hive.connect.assert_called_once_with(
        host='somehost',
        username='anon',
        configuration={
            'tez.queue.name': 'default',
        }
    )


@pytest.mark.parametrize('field_type', ['int', 'string', 'date', 'timestamp', 'interval', 'bigint', 'decimal',
                                        'double', 'float'])
def test_write_default_values(mocker, tmpdir, hive_cursor, field_type, hive_runner):
    # arrange
    hive_cursor.fetchall.return_value = [
        ('field1', 'int', ''),
        ('field2', field_type, ''),
        ('field3', 'string', '')
    ]

    test_file = tmpdir.join('test.csv')
    test_file.write('field1,field3\n1,string')

    # act
    run_test_query(
        query='select 1',
        expected={},
        tables={'expected.table': test_file},
        runner=hive_runner,
        test_schema='tezt'
    )

    # assert
    assert hive_cursor.execute.mock_calls == [
        mocker.call('DROP TABLE IF EXISTS tezt.expected_table'),
        mocker.call('CREATE TABLE IF NOT EXISTS tezt.expected_table LIKE expected.table'),
        mocker.call('DESC tezt.expected_table'),
        mocker.call('INSERT INTO TABLE tezt.expected_table SELECT 1, NULL, \'string\' FROM tezt.dummy'),
        mocker.call('select 1'),
        mocker.call('DROP TABLE IF EXISTS tezt.expected_table')
    ]


@pytest.mark.parametrize('field_type, csv_line, projection1, projection2', [
    ('array<string>', '1,\'""\'\n2,\'"1","2","3"\'', '1, array("")', '2, array("1","2","3")'),
    ('array<string>', '1,\'\'\n2,\'"1","2","3"\'', '1, array()', '2, array("1","2","3")'),
    ('string', '1,NULL\n2,\'string\'', '1, NULL', '2, \'string\''),
    ('int', '1,NULL\n2,8', '1, NULL', '2, 8'),
    ('double', '1,NULL\n2,1.598', '1, NULL', '2, 1.598'),
    ('date', '1,NULL\n2,\'2019-01-01\'', '1, NULL', '2, \'2019-01-01\''),
    ('boolean', '1,NULL\n2,true', '1, NULL', '2, true'),
    ('map<varchar,varchar>', '1,\'\'\n2,\'"1","2"\'', '1, map()', '2, map("1","2")'),
    ('map<varchar,varchar>', '1,NULL\n2,\'"1","2"\'', '1, map()', '2, map("1","2")')
])
def test_write_null_values_in_expected(mocker, tmpdir, hive_cursor, field_type, csv_line, projection1, projection2,
                                       hive_runner):
    # arrange
    hive_cursor.fetchall.return_value = [
        ('field1', 'int', ''),
        ('field2', field_type, '')
    ]

    test_file = tmpdir.join('test.csv')
    test_file.write('field1,field2\n{}'.format(csv_line))

    # act
    run_test_query(
        query='select 1',
        tables={'expected.table': test_file},
        expected=dict(),
        test_schema='tezt',
        runner=hive_runner,
    )

    # assert
    assert hive_cursor.execute.mock_calls == [
        mocker.call('DROP TABLE IF EXISTS tezt.expected_table'),
        mocker.call('CREATE TABLE IF NOT EXISTS tezt.expected_table LIKE expected.table'),
        mocker.call('DESC tezt.expected_table'),
        mocker.call('INSERT INTO TABLE tezt.expected_table SELECT {} FROM tezt.dummy '
                    'UNION ALL SELECT {} FROM tezt.dummy'.format(projection1, projection2)),
        mocker.call('select 1'),
        mocker.call('DROP TABLE IF EXISTS tezt.expected_table')
    ]


@pytest.mark.parametrize('field_type, csv_line, projection1, projection2', [
    ('array<string>', '1,\'""\'\n2,\'"1","2","3"\'', '1, array("")', '2, array("1","2","3")'),
    ('array<string>', '1,\'\'\n2,\'"1","2","3"\'', '1, array()', '2, array("1","2","3")'),
    ('string', '1,NULL\n2,\'string\'', '1, NULL', '2, \'string\''),
    ('int', '1,NULL\n2,8', '1, NULL', '2, 8'),
    ('double', '1,NULL\n2,1.598', '1, NULL', '2, 1.598'),
    ('date', '1,NULL\n2,\'2019-01-01\'', '1, NULL', '2, \'2019-01-01\''),
    ('boolean', '1,NULL\n2,true', '1, NULL', '2, true'),
])
def test_write_null_values_in_source(mocker, tmpdir, hive_cursor, field_type, csv_line, projection1, projection2,
                                     hive_runner):
    # arrange
    hive_cursor.fetchall.return_value = [
        ('field1', 'int', ''),
        ('field2', field_type, '')
    ]

    test_file = tmpdir.join('test.csv')
    test_file.write('field1,field2\n{}'.format(csv_line))

    # act
    run_test_query(
        query='select 1',
        tables={'source.table': test_file},
        expected=dict(),
        test_schema='tezt',
        runner=hive_runner,
    )

    # assert
    assert hive_cursor.execute.mock_calls == [
        mocker.call('DROP TABLE IF EXISTS tezt.source_table'),
        mocker.call('CREATE TABLE IF NOT EXISTS tezt.source_table LIKE source.table'),
        mocker.call('DESC tezt.source_table'),
        mocker.call('INSERT INTO TABLE tezt.source_table SELECT {} FROM tezt.dummy '
                    'UNION ALL SELECT {} FROM tezt.dummy'.format(projection1, projection2)),
        mocker.call('select 1'),
        mocker.call('DROP TABLE IF EXISTS tezt.source_table')
    ]


def test_unicode_in_array(mocker, tmpdir, hive_cursor, hive_runner):
    # arrange
    hive_cursor.fetchall.return_value = [('field1', 'array<string>', '')]

    test_file = tmpdir.join('test.csv')
    test_file.write(u'field1\n\'"Юникод1","Юникод2"\''.encode('utf8'), mode='wb')

    calls = [
        mocker.call('DROP TABLE IF EXISTS tezt.source_table'),
        mocker.call('CREATE TABLE IF NOT EXISTS tezt.source_table LIKE source.table'),
        mocker.call('DESC tezt.source_table'),
        mocker.call(
            u'INSERT INTO TABLE tezt.source_table SELECT '
            u'array("\u042e\u043d\u0438\u043a\u043e\u04341","\u042e\u043d\u0438\u043a\u043e\u04342") FROM tezt.dummy'
        ),
        mocker.call('select 1'),
        mocker.call('DROP TABLE IF EXISTS tezt.source_table')
    ]

    # act
    run_test_query(
        query='select 1',
        tables={'source.table': test_file},
        expected=dict(),
        test_schema='tezt',
        runner=hive_runner,
    )

    # assert
    assert hive_cursor.execute.mock_calls == calls


def test_unicode_in_map(mocker, tmpdir, hive_cursor, hive_runner):
    # arrange

    hive_cursor.fetchall.return_value = [('field1', 'map<string,string>', '')]
    hive_cursor.description.side_effect = ['a', 'b', 'c']

    test_file = tmpdir.join('test.csv')
    test_file.write(u'field1\n\'"key1","Юникод1","key2","Юникод2"\''.encode('utf8'), mode='wb')

    calls = [
        mocker.call('DROP TABLE IF EXISTS tezt.source_table'),
        mocker.call('CREATE TABLE IF NOT EXISTS tezt.source_table LIKE source.table'),
        mocker.call('DESC tezt.source_table'),
        mocker.call(
            u'INSERT INTO TABLE tezt.source_table SELECT map("key1","\u042e\u043d\u0438\u043a\u043e\u04341","key2","\u042e\u043d\u0438\u043a\u043e\u04342") FROM tezt.dummy'),
        mocker.call('select 1'),
        mocker.call('DROP TABLE IF EXISTS tezt.source_table')
    ]

    # act
    run_test_query(
        query='select 1',
        tables={'source.table': test_file},
        expected=dict(),
        test_schema='tezt',
        runner=hive_runner,
    )

    # assert
    assert hive_cursor.execute.mock_calls == calls
