package org.utdr.sprites;

import android.content.*;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;
import java.io.*;

/** Read-only exports, accessible to other apps only with an explicit URI grant. */
public class ExportProvider extends ContentProvider {
 public boolean onCreate(){return true;}
 private File file(Uri uri) throws FileNotFoundException {
  if(!"org.utdr.sprites.exports".equals(uri.getAuthority()) || uri.getPathSegments().size()!=2)throw new FileNotFoundException();
  String token=uri.getPathSegments().get(0),name=uri.getLastPathSegment();
  if(!token.matches("[a-f0-9-]{36}")||name.contains("/")||name.contains("\\")||name.equals(".")||name.equals(".."))throw new FileNotFoundException();
  File f=new File(new File(new File(getContext().getFilesDir(),"exports"),token),name);
  if(!f.isFile())throw new FileNotFoundException();return f;
 }
 public static String mime(String name){return name.endsWith(".png")?"image/png":name.endsWith(".gif")?"image/gif":"application/zip";}
 public String getType(Uri uri){return mime(uri.getLastPathSegment());}
 public ParcelFileDescriptor openFile(Uri uri,String mode)throws FileNotFoundException{if(!"r".equals(mode))throw new FileNotFoundException("Read only");return ParcelFileDescriptor.open(file(uri),ParcelFileDescriptor.MODE_READ_ONLY);}
 public Cursor query(Uri uri,String[] projection,String selection,String[] args,String order){
  try{File f=file(uri);String[] columns=projection==null?new String[]{OpenableColumns.DISPLAY_NAME,OpenableColumns.SIZE}:projection;MatrixCursor c=new MatrixCursor(columns);Object[] row=new Object[columns.length];for(int i=0;i<columns.length;i++)row[i]=OpenableColumns.DISPLAY_NAME.equals(columns[i])?f.getName():OpenableColumns.SIZE.equals(columns[i])?f.length():null;c.addRow(row);return c;}catch(IOException e){return null;}
 }
 public Uri insert(Uri u,ContentValues v){throw new UnsupportedOperationException();}
 public int update(Uri u,ContentValues v,String s,String[] a){throw new UnsupportedOperationException();}
 public int delete(Uri u,String s,String[] a){throw new UnsupportedOperationException();}
}
