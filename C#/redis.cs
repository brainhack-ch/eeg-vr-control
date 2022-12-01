using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using StackExchange.Redis;

public class Redis : MonoBehaviour
{
    public IDatabase db;
    private float z;
    // Start is called before the first frame update
    void Start()
    {
        ConnectionMultiplexer redis = ConnectionMultiplexer.Connect("localhost");
        db = redis.GetDatabase();
        Debug.Log(db);
        z = this.transform.position.z;
        Debug.Log(x);
    }

    // Update is called once per frame
    void Update()
    {
        string value = db.StringGet("mykey");
        Debug.Log(value);
        z = float.Parse(value);
        this.transform.position = new Vector3(transform.position.x, transform.position.y, z);
    }
}
