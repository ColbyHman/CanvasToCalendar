import java.io.*;
import java.lang.reflect.Array;
import java.util.ArrayList;
import java.util.Scanner;
import java.net.*;

public class MapsTest {

    public String processString(String string, Boolean bool){

        string = string.trim();
        String[] splitString = string.split(" ");
        String processedString = "";

        for(int i = 0; i < splitString.length; i++){
            processedString += splitString[i];
            processedString += "+";
        }
        if(bool)
            processedString += "Bethlehem,+PA+18018";

        return processedString;
    }


    public ArrayList<String[]> generateLocationList() throws FileNotFoundException {
        Scanner scanner = new Scanner(new File("resources/locations.csv"));
        ArrayList<String[]> locations = new ArrayList();
        while(scanner.hasNextLine()){
            String line = scanner.nextLine();
            String[] data = line.split(",");
            locations.add(data);
        }

        return null;
    }

    public static void main(String[] args) throws IOException {
        MapsTest map = new MapsTest();
        ArrayList<String[]> locations = map.generateLocationList();

        String desiredLocation = "Colonial Hall";
        String crimeLocation = "Hillside VI";
        String desiredAddress = "";
        String crimeAddress = "";

        for(int i = 0; i < locations.size(); i++){
            String[] line = locations.get(i);
            if(line[0].equals(desiredLocation)) {
                System.out.println("Location Name : " + line[0] + "\n\t\t Address : " + line[1]);
                desiredAddress = line[1];
                System.out.println(desiredAddress);
            }
            if(line[0].equals(crimeLocation)) {
                System.out.println("Location Name : " + line[0] + "\n\t\t Address : " + line[1]);
                crimeAddress = line[1];
                System.out.println(crimeAddress);
            }
        }

        String processedAddress = map.processString(desiredAddress, true);
        String processedCrimeAddress = map.processString(crimeAddress, true);
        String processedDesiredLocation = map.processString(desiredLocation, false);

        //Process data to create URL
        String zoom = "16";
        String crimeMarker = "flag-8B0000-EVENT";
        String locationMarker = "marker-lg-3B5998-22407F";
        String key = "UDxbwAfazAkmB9R6pD6gdkK9hCgVhAB1";
        String center = desiredLocation;
        String typeOfMap = "map";
        String banner = "Event+in+Relation+to+:+"+processedDesiredLocation+"|lg-top-3B5998-22407F";
        String size = "800,800";



        System.out.println(processedAddress);
        System.out.println(processedCrimeAddress);

        String urlText = "https://www.mapquestapi.com/staticmap/v5/map?key="+key
                +"&center="+processedAddress+"&locations="+processedCrimeAddress+"|"+
                crimeMarker+"||"+processedAddress+"|"+locationMarker+"&zoom="+
                zoom+"&banner="+banner+"&type="+typeOfMap+"&size="+size;

        URL url = new URL(urlText);
        HttpURLConnection con = (HttpURLConnection) url.openConnection();
        con.setRequestMethod("GET");

        InputStream inputStream = con.getInputStream();
        FileOutputStream fileOutputStream = new FileOutputStream(new File("resources/image.png"));
        int bytesRead = -1;
        byte[] buffer = new byte[1024];
        while ((bytesRead = inputStream.read(buffer)) != -1) {
            fileOutputStream.write(buffer, 0, bytesRead);
        }

        fileOutputStream.close();
        inputStream.close();
    }




}
