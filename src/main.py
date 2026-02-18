from cs import CloudStack

cs = CloudStack(
    endpoint="http://10.10.5.52:8080/client/api",
    key="5VRUsYejS6eji7AOFM-pbiZlu-i9aIXoEvHUdN1onimGL5vcC1zp1X1HDcrQjvbl47k96hA-7z1c8c3V6Re6tg",
    secret="YBW-Cl8CJZnTJp14laXW0zvArfso-YHfwoq6fBNI9HWZ5SuBYv6KLE97A4lNlq6lpzt_mPUFCdDzFa6ZhyqSqA",
)

print(cs.listUsers(listall="true", username="fc56908"))
