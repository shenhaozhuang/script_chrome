#!/bin/bash
#USERNAME="222"
#PASSWORD=""
#baseUrl="http://127.0.0.1:7001"
#baseUrl="https://10.239.156.21:8443"
baseUrl="https://192.168.3.7:8443"
uploadResultUrl="upload/uploadEnvAndResult"
uploadDetailUrl="upload/uploadDetail"
USERNAME=""
PASSWORD=""
FILEPATH=""
#set -x

#read the arguments
TEMP=`getopt -o u:p:f: --long u-long,p-long:,f-long:: \
     -n 'example.bash' -- "$@"`
[ $? -ne 0 ] && usage
#eval set -- "${ARGS}"
eval set -- "$TEMP"
# getopt -- process

while true ; do
    case "$1" in
        -u|--username) echo "$2"; USERNAME="$2" ; shift ;;
        -p|--password)  echo "$2";  PASSWORD="$2" ; shift ;;
        -f|--filepath)  echo "$2";  FILEPATH="$2" ; shift ;;
        --) shift ; break ;;
        *) echo "Internal error!" ; exit 1 ;;
    esac
    shift
done
#echo "Remaining arguments:"
#for arg do
#   echo '--> '"\`$TEMP'" ;
#done


#extract
parse_json(){
	resp=$1
	key=$2
	if [[ "$resp" =~ '"'${key}'":'[\"]?([^,\"]*)[\"]?',' ]]; then
		echo ${BASH_REMATCH[1]}
	fi
	#echo "${1//\"/}" | sed "s/.*$2:\([^,}]*\).*/\1/"
}
#judge password is exist
#if [ (-z "$PASSWORD") || (-z "$USERNAME") || (-z "$FILEPATH") ]
if [ -z "$PASSWORD"  ] || [ -z "$USERNAME"  ] || [ -z "$FILEPATH"  ]
then
    echo "three parameter must not be empty, please check!"
    exit 0  
    
fi

if [ ! -f "$FILEPATH" ]
then
    echo "file doesn't exist, please check!"
    exit 0
fi

echo "test"
#login------------------------------------------------------------------------------
echo "loading to login"
#response=$(curl -d "userName=$USERNAME&passWord=$PASSWORD" "$baseUrl/generateInnerToken" -s)
response=$(curl -d "userName=$USERNAME&passWord=$PASSWORD" "$baseUrl/generateInnerToken" -k)
echo ${response}
echo $(parse_json "${response}" "message")
echo $(parse_json "${response}" "code")
echo $(parse_json "${response}" "token")

if [[ "$(parse_json "${response}" "code")" != 200 ]]
then
    echo "login error!"
    exit 0 
fi
echo "login success!"

#upload-----------------------------------------------------------------------------
echo ${response}
token=$(parse_json "${response}" "token")
echo "loading to upload result"
uploadResult=$(curl "$baseUrl/$uploadDetailUrl" -F "file=@$FILEPATH" -H "Authorization:$token" -k)
if [ "$(parse_json "${uploadResult}" "code")" == 200  ]
then
    echo "upload result success!"
else
    echo "upload result error!"
    echo "$(parse_json "${uploadResult}" "message")"
fi


