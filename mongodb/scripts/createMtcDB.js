use admin;
db.createUser({user: "dbadmin", pwd:"password", roles: ["readWriteAnyDatabase"]});

use mtc;
db.createUser({user: "dbadmin", pwd:"password", roles: ["readWrite"]});
