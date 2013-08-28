import MySQLdb

def is_partner_program(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select Collections from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()
    if (data):
        return data[0].find('GettyDistribution') != -1
    else:
        return 0

def get_file_type(assetId):
    connection = MySQLdb.connect('reporting2.istockphoto.com', 'maint', 'ngTX6Kupa$c', 'istockphoto')
    cursor = connection.cursor()
    query = 'select AbstractTypeID from AbstractFile where ID = %d' % assetId
    cursor.execute(query)
    data = cursor.fetchone()
    print 'data', data
    if not data:
        return None

    data = data[0]

    if data == 1:
        return 'photo'
    elif data == 4:
        return 'flash'
    elif data == 7:
        return 'vector'
    elif data == 8:
        return 'video'
    else:
        return None
